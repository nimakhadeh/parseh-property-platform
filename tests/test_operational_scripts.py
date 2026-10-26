"""Run real operational shell scripts against isolated command stubs and temp data.

No PostgreSQL, systemd, root access, or /opt writes are required.
"""
import gzip
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OperationalScriptsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.bin = self.project / "bin"
        self.bin.mkdir()
        self.tmp = self.project / "tmp"
        self.tmp.mkdir()
        (self.project / ".env").write_text(
            'DB_NAME=parseh_test\nDB_USER=parseh_user\nDB_PASSWORD="test secret"\n'
            'SITE_NAME="پلتفرم املاک پارسه"\nRCLONE_REMOTE=\n'
        )
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                        PARSEH_PROJECT_DIR=str(self.project), TMPDIR=str(self.tmp),
                        COMMAND_LOG=str(self.project / "commands"),
                        SQL_LOG=str(self.project / "restored.sql"),
                        STUB_ACTIVE_SERVICES="parseh parseh-celery")
        self.stub("pg_dump", '''#!/usr/bin/env bash
if [[ "${STUB_DUMP_STATUS:-0}" != 0 ]]; then
    echo 'partial SQL'; echo 'pg_dump connection failed' >&2; exit "$STUB_DUMP_STATUS"
fi
printf 'CREATE TABLE example (id integer);\nINSERT INTO example VALUES (1);\n'
''')
        self.stub("sudo", '#!/usr/bin/env bash\nexec "$@"\n')
        self.stub("systemctl", '''#!/usr/bin/env bash
echo "systemctl $*" >> "$COMMAND_LOG"
case "$1" in
    is-active) [[ " ${STUB_ACTIVE_SERVICES:-} " == *" ${@: -1} "* ]] ;;
    stop) exit "${STUB_STOP_STATUS:-0}" ;;
    start) exit "${STUB_START_STATUS:-0}" ;;
    *) exit 99 ;;
esac
''')
        self.stub("psql", '''#!/usr/bin/env bash
echo "psql $*" >> "$COMMAND_LOG"
for arg in "$@"; do
    case "$arg" in --file=*) cat "${arg#--file=}" > "$SQL_LOG" ;; esac
done
exit "${STUB_PSQL_STATUS:-0}"
''')

    def stub(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def run_script(self, name, *args, answer="", **env):
        return subprocess.run(["bash", str(ROOT / name), *map(str, args)],
                              input=answer, text=True, capture_output=True,
                              env=dict(self.env, **env), check=False)

    def commands(self):
        path = self.project / "commands"
        return path.read_text() if path.exists() else ""

    def backup(self, sql=b"CREATE TABLE example(id integer);\n"):
        path = self.project / "input.sql.gz"
        path.write_bytes(gzip.compress(sql))
        return path

    def test_failed_dump_does_not_publish_or_delete_previous_backup(self):
        backup_dir = self.project / "backups"
        backup_dir.mkdir()
        old = backup_dir / "parseh_db_previous.sql.gz"
        old.write_bytes(gzip.compress(b"previous valid SQL"))
        previous_time = time.time() - 35 * 24 * 60 * 60
        os.utime(old, (previous_time, previous_time))
        result = self.run_script("backup_db.sh", STUB_DUMP_STATUS="2")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(list(backup_dir.iterdir()), [old])
        self.assertNotIn("با موفقیت", result.stdout)

    def test_successful_dump_publishes_complete_private_gzip(self):
        result = self.run_script("backup_db.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        backups = list((self.project / "backups").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertIn(b"INSERT INTO example VALUES (1)", gzip.decompress(backups[0].read_bytes()))
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)

    def test_cloud_failure_keeps_successful_local_backup(self):
        with (self.project / ".env").open("a") as stream:
            stream.write('RCLONE_REMOTE=test:backups\n')
        self.stub("rclone", '#!/usr/bin/env bash\nexit 1\n')
        result = self.run_script("backup_db.sh")
        self.assertEqual(result.returncode, 2)
        backups = list((self.project / "backups").glob("*.sql.gz"))
        self.assertEqual(len(backups), 1)
        self.assertTrue(gzip.decompress(backups[0].read_bytes()))

    def test_corrupt_backup_does_not_stop_services(self):
        path = self.project / "corrupt.sql.gz"
        path.write_bytes(b"not gzip")
        result = self.run_script("restore_db.sh", path, answer="yes\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.commands(), "")
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_empty_sql_does_not_stop_services(self):
        result = self.run_script("restore_db.sh", self.backup(b""), answer="yes\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.commands(), "")

    def test_restore_replaces_schema_transactionally_and_recovers_active_services(self):
        result = self.run_script("restore_db.sh", self.backup(), answer="yes\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.commands()
        self.assertIn("--single-transaction", commands)
        self.assertIn("--set=ON_ERROR_STOP=1", commands)
        self.assertIn("DROP SCHEMA public CASCADE; CREATE SCHEMA public", commands)
        self.assertIn("systemctl stop parseh parseh-celery\n", commands)
        self.assertIn("systemctl start parseh parseh-celery\n", commands)
        self.assertNotIn("start parseh parseh-celery parseh-celery-beat", commands)
        self.assertEqual((self.project / "restored.sql").read_bytes(), b"CREATE TABLE example(id integer);\n")
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_failed_sql_restore_recovers_services_without_success_message(self):
        result = self.run_script("restore_db.sh", self.backup(), answer="yes\n",
                                 STUB_PSQL_STATUS="3")
        self.assertEqual(result.returncode, 3)
        self.assertIn("systemctl start parseh parseh-celery\n", self.commands())
        self.assertNotIn("با موفقیت", result.stdout)
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_partial_stop_failure_recovers_services_without_running_sql(self):
        result = self.run_script("restore_db.sh", self.backup(), answer="yes\n",
                                 STUB_STOP_STATUS="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("systemctl start parseh parseh-celery\n", self.commands())
        self.assertNotIn("psql ", self.commands())

    def test_restart_failure_is_not_reported_as_success(self):
        result = self.run_script("restore_db.sh", self.backup(), answer="yes\n",
                                 STUB_START_STATUS="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("با موفقیت", result.stdout)

    def test_cancel_does_not_touch_services_or_database(self):
        result = self.run_script("restore_db.sh", self.backup(), answer="no\n")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.commands(), "")

    def test_restore_does_not_start_previously_inactive_services(self):
        result = self.run_script("restore_db.sh", self.backup(), answer="yes\n",
                                 STUB_ACTIVE_SERVICES="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("systemctl start", self.commands())
        self.assertNotIn("systemctl stop", self.commands())


class DeploymentConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Execute the actual GitHub Actions validation shell block without extra YAML dependencies.
        workflow = (ROOT / ".github/workflows/deploy.yml").read_text()
        block = workflow.split("        id: deployment\n", 1)[1]
        lines = block.split("        run: |\n", 1)[1].splitlines()
        script = []
        for line in lines:
            if line and not line.startswith("          "):
                break
            script.append(line[10:])
        cls.script = "\n".join(script)

    def validate(self, **values):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "outputs"
            env = dict(os.environ, GITHUB_OUTPUT=str(output),
                       VPS_HOST="", VPS_USER="", SSH_PRIVATE_KEY="")
            env.update(values)
            result = subprocess.run(["bash", "-c", self.script], env=env,
                                    capture_output=True, text=True, check=False)
            return result, output.read_text() if output.exists() else ""

    def test_unconfigured_optional_deployment_is_skipped(self):
        result, output = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("configured=false", output)
        self.assertIn("Deployment skipped", result.stdout)

    def test_partial_configuration_fails_with_missing_name(self):
        result, output = self.validate(VPS_HOST="vps.example.com")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing VPS_USER", result.stdout)
        self.assertNotIn("configured=true", output)

    def test_complete_configuration_does_not_print_credentials(self):
        result, output = self.validate(VPS_HOST="vps.example.com", VPS_USER="deploy",
                                       SSH_PRIVATE_KEY="private-credential")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("configured=true", output)
        self.assertNotIn("private-credential", result.stdout + result.stderr)


class DeploymentRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.origin = self.directory / "origin"
        self.origin.mkdir()
        self.checkout = self.directory / "deployed"
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
        self.git("init", "-b", "main", cwd=self.origin)
        self.git("config", "user.email", "test@example.com", cwd=self.origin)
        self.git("config", "user.name", "Script Test", cwd=self.origin)
        (self.origin / ".gitignore").write_text(".env\nvenv/\n")
        (self.origin / "revision.txt").write_text("tested version")
        self.git("add", ".", cwd=self.origin)
        self.git("commit", "-m", "tested commit", cwd=self.origin)
        self.tested_sha = self.git("rev-parse", "HEAD", cwd=self.origin).stdout.strip()
        (self.origin / "revision.txt").write_text("newer untested version")
        self.git("commit", "-am", "newer main", cwd=self.origin)
        self.git("clone", "--no-hardlinks", str(self.origin), str(self.checkout))
        (self.checkout / ".env").write_text('DB_PASSWORD="test password"\n')
        python = self.checkout / "venv/bin/python"
        python.parent.mkdir(parents=True)
        python.write_text('#!/bin/sh\nprintf "%s|%s|%s\\n" "$DJANGO_SETTINGS_MODULE" "$DB_PASSWORD" "$*" >> "$PYTHON_LOG"\n')
        python.chmod(0o755)
        bin_dir = self.directory / "bin"
        bin_dir.mkdir()
        sudo = bin_dir / "sudo"
        sudo.write_text('#!/bin/sh\necho "$*" >> "$SERVICE_LOG"\n')
        sudo.chmod(0o755)
        self.env.update(PATH=f"{bin_dir}:{self.env['PATH']}", DEPLOY_SHA=self.tested_sha,
                        PYTHON_LOG=str(self.directory / "python.log"),
                        SERVICE_LOG=str(self.directory / "services.log"),
                        DJANGO_SETTINGS_MODULE="config.settings.local_test")
        workflow = (ROOT / ".github/workflows/deploy.yml").read_text()
        script = workflow.split("          script: |\n", 1)[1]
        self.script = "\n".join(line[12:] for line in script.splitlines())
        self.script = self.script.replace("cd /opt/parseh_project", 'cd "' + str(self.checkout) + '"')

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.directory,
                              env=self.env, capture_output=True, text=True, check=True)

    def deploy(self):
        return subprocess.run(["bash", "-c", self.script], env=self.env,
                              capture_output=True, text=True, check=False)

    def test_deploys_tested_commit_when_main_has_advanced_and_exports_env(self):
        result = self.deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.checkout).stdout.strip(), self.tested_sha)
        self.assertEqual((self.checkout / "revision.txt").read_text(), "tested version")
        commands = (self.directory / "python.log").read_text().splitlines()
        self.assertEqual(len(commands), 3)
        self.assertTrue(all(line.startswith("config.settings.production|test password|") for line in commands))
        self.assertIn("manage.py migrate --noinput", commands[1])
        self.assertEqual((self.directory / "services.log").read_text(),
                         "systemctl restart parseh parseh-celery parseh-celery-beat\n")

    def test_deployment_refuses_to_overwrite_modified_tracked_files(self):
        (self.checkout / "revision.txt").write_text("operator changes")
        result = self.deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.checkout / "revision.txt").read_text(), "operator changes")
        self.assertFalse((self.directory / "python.log").exists())


if __name__ == "__main__":
    unittest.main()
