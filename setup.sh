#!/usr/bin/env bash
# نصب روی Ubuntu 22.04 / 24.04 از یک checkout گیت؛ اجرا: sudo bash setup.sh
set -euo pipefail
umask 022

PROJECT_DIR="/opt/parseh_project"
DEPLOY_USER="${SUDO_USER:-root}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
info() { echo "[اطلاعات] $1"; }
error() { echo "[خطا] $1" >&2; exit 1; }
[[ ${EUID} -eq 0 ]] || error "با sudo bash setup.sh اجرا کنید."

# Python پیش‌فرض هر دو نسخه اوبونتو با Django 5.2 سازگار است.
apt-get update -y
apt-get install -y python3 python3-venv python3-pip postgresql postgresql-contrib \
    libpq-dev binutils redis-server nginx git curl build-essential openssl \
    certbot python3-certbot-nginx

SOURCE_COMMIT=$(git -c safe.directory="${SOURCE_DIR}" -C "${SOURCE_DIR}" rev-parse HEAD) || error "نصب باید از checkout گیت اجرا شود."
REPOSITORY_URL=$(git -c safe.directory="${SOURCE_DIR}" -C "${SOURCE_DIR}" remote get-url origin) || error "remote با نام origin تنظیم نشده است."
if [[ "${SOURCE_DIR}" != "${PROJECT_DIR}" ]]; then
    if [[ ! -e "${PROJECT_DIR}" ]]; then
        git clone "${REPOSITORY_URL}" "${PROJECT_DIR}"
        git -c safe.directory="${PROJECT_DIR}" -C "${PROJECT_DIR}" checkout --detach "${SOURCE_COMMIT}"
    elif ! git -c safe.directory="${PROJECT_DIR}" -C "${PROJECT_DIR}" rev-parse --git-dir >/dev/null 2>&1; then
        error "${PROJECT_DIR} از قبل وجود دارد ولی checkout گیت نیست؛ ابتدا داده‌ها و .env را نگه‌داری و مقصد را برای clone آماده کنید."
    else
        info "checkout موجود حفظ شد؛ بروزرسانی کد را با پایپلاین انجام دهید."
    fi
fi
cd "${PROJECT_DIR}"
mkdir -p run logs media staticfiles

if [[ ! -f .env ]]; then
    read -rp "دامنه سایت برای گواهی HTTPS (مثلاً example.com): " DOMAIN
    [[ "${DOMAIN}" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}$ ]] || error "دامنه معتبر با DNS متصل به سرور لازم است."
    install -m 600 .env.example .env
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|; s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=${DOMAIN},localhost,127.0.0.1|; s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=https://${DOMAIN}|; s|^DB_PASSWORD=.*|DB_PASSWORD=${DB_PASSWORD}|" .env
fi
set -a
source ./.env
set +a
DOMAIN="${ALLOWED_HOSTS%%,*}"
[[ "${DOMAIN}" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}$ ]] || error "اولین ALLOWED_HOSTS باید دامنه سایت با DNS معتبر باشد."
[[ "${DB_NAME}" =~ ^[a-z_][a-z0-9_]*$ && "${DB_USER}" =~ ^[a-z_][a-z0-9_]*$ ]] || error "DB_NAME و DB_USER باید شناسه ساده PostgreSQL باشند."
# این نصب دیتابیس محلی را مدیریت می‌کند؛ اتصال راه دور باید جداگانه آماده شود.
[[ "${DB_HOST:-127.0.0.1}" == "127.0.0.1" || "${DB_HOST:-127.0.0.1}" == "localhost" ]] || error "setup.sh فقط PostgreSQL محلی را ایجاد می‌کند."

systemctl enable --now postgresql redis-server
# مقدار رمز از stdin ارسال می‌شود تا در آرگومان قابل مشاهده پردازش نباشد.
SQL_DB_PASSWORD="${DB_PASSWORD//\'/\'\'}"
sudo -u postgres psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --set=db_name="${DB_NAME}" --set=db_user="${DB_USER}" <<SQL
SET standard_conforming_strings = on;
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'db_user', '${SQL_DB_PASSWORD}')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'db_user') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'db_name', :'db_user')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'db_name') \gexec
SQL
sudo -u postgres psql --no-psqlrc --set=ON_ERROR_STOP=1 --dbname="${DB_NAME}" \
    --set=db_user="${DB_USER}" <<'SQL'
ALTER SCHEMA public OWNER TO :"db_user";
SQL

python3 -m venv venv
venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install -r requirements/production.txt
venv/bin/python manage.py migrate --noinput
venv/bin/python manage.py collectstatic --noinput

# کد و checkout برای deploy user؛ فقط داده‌های زمان اجرا برای www-data قابل نوشتن‌اند.
chown -R "${DEPLOY_USER}:www-data" "${PROJECT_DIR}"
chmod 640 .env
chown -R www-data:www-data run logs media
cp parseh.service parseh-celery.service parseh-celery-beat.service /etc/systemd/system/
systemctl daemon-reload

NGINX_CONF="/etc/nginx/sites-available/parseh"
cp nginx.conf "${NGINX_CONF}"
sed -i "s/server_name example.com www.example.com;/server_name ${DOMAIN};/" "${NGINX_CONF}"
ln -sf "${NGINX_CONF}" /etc/nginx/sites-enabled/parseh
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# گواهی قبل از ارائه سایت فعال می‌شود. خطای صدور گواهی نصب موفق گزارش نمی‌شود.
certbot --nginx --redirect -d "${DOMAIN}" --non-interactive --agree-tos -m "admin@${DOMAIN}"
if grep -q '^SECURE_SSL_REDIRECT=' .env; then
    sed -i 's/^SECURE_SSL_REDIRECT=.*/SECURE_SSL_REDIRECT=True/' .env
else
    echo 'SECURE_SSL_REDIRECT=True' >> .env
fi
systemctl enable --now parseh parseh-celery parseh-celery-beat
systemctl restart parseh parseh-celery parseh-celery-beat
info "نصب کامل شد: https://${DOMAIN}"
info "برای ساخت مدیر: cd ${PROJECT_DIR}; set -a; source ./.env; set +a; venv/bin/python manage.py createsuperuser"
