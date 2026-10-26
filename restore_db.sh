#!/usr/bin/env bash
# بازیابی بک‌آپ SQL پروژه در schema عمومی؛ اجرا: sudo bash restore_db.sh file.sql.gz
# DROP و بازیابی در یک transaction انجام می‌شوند؛ خطا داده‌های فعلی را نگه می‌دارد.
set -euo pipefail
umask 077

PROJECT_DIR="${PARSEH_PROJECT_DIR:-/opt/parseh_project}"
BACKUP_FILE="${1:-}"
if [[ -z "${BACKUP_FILE}" || ! -f "${BACKUP_FILE}" ]]; then
    echo "استفاده: bash restore_db.sh <مسیر فایل بک‌آپ.sql.gz>" >&2
    exit 1
fi

set -a
source "${PROJECT_DIR}/.env"
set +a

# پیش از توقف سرویس‌ها، کامل بودن فایل فشرده و امکان خواندن آن بررسی می‌شود.
TEMP_FILE=$(mktemp "${TMPDIR:-/tmp}/parseh-restore.XXXXXX")
ACTIVE_SERVICES=()
SERVICES_STOPPED=0
cleanup() {
    local result=$?
    trap - EXIT
    rm -f -- "${TEMP_FILE}"
    if [[ "${SERVICES_STOPPED}" -eq 1 ]]; then
        if ! sudo systemctl start "${ACTIVE_SERVICES[@]}"; then
            echo "خطا: راه‌اندازی مجدد سرویس‌ها ناموفق بود؛ وضعیت systemd را بررسی کنید." >&2
            result=1
        fi
    fi
    exit "${result}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
gzip --decompress --stdout -- "${BACKUP_FILE}" > "${TEMP_FILE}"
if [[ ! -s "${TEMP_FILE}" ]]; then
    echo "خطا: فایل SQL بک‌آپ خالی است." >&2
    exit 1
fi

read -rp "این کار schema عمومی دیتابیس '${DB_NAME}' را جایگزین می‌کند. مطمئنید؟ (yes/no): " CONFIRM
if [[ "${CONFIRM}" != "yes" ]]; then
    echo "لغو شد."
    exit 0
fi

for service in parseh parseh-celery parseh-celery-beat; do
    if sudo systemctl is-active --quiet "${service}"; then
        ACTIVE_SERVICES+=("${service}")
    fi
done
if [[ "${#ACTIVE_SERVICES[@]}" -gt 0 ]]; then
    # قبل از stop علامت‌گذاری می‌شود تا شکست جزئی stop هم قابل بازیابی باشد.
    SERVICES_STOPPED=1
    sudo systemctl stop "${ACTIVE_SERVICES[@]}"
fi

echo "[$(date)] بازیابی دیتابیس از ${BACKUP_FILE}..."
# نقش دیتابیس باید مالک schema عمومی باشد (setup.sh این مالکیت را تنظیم می‌کند).
# --single-transaction همه دستورها، از جمله DROP، را با هم commit یا rollback می‌کند.
PGPASSWORD="${DB_PASSWORD}" psql --no-psqlrc --set=ON_ERROR_STOP=1 \
    --single-transaction -h "${DB_HOST:-127.0.0.1}" -p "${DB_PORT:-5432}" \
    -U "${DB_USER}" --dbname="${DB_NAME}" \
    --command='DROP SCHEMA public CASCADE; CREATE SCHEMA public AUTHORIZATION CURRENT_USER;' \
    --file="${TEMP_FILE}"

if [[ "${SERVICES_STOPPED}" -eq 1 ]]; then
    sudo systemctl start "${ACTIVE_SERVICES[@]}"
    SERVICES_STOPPED=0
fi
echo "[$(date)] بازیابی با موفقیت انجام شد."
