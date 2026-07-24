#!/usr/bin/env bash
# ============================================================================
# بازیابی دیتابیس پلتفرم املاک پارسه از یک فایل بک‌آپ
# استفاده: sudo bash restore_db.sh backups/parseh_db_2026-01-15_03-00.sql.gz
#
# هشدار: این اسکریپت دیتابیس فعلی را کاملاً با محتوای بک‌آپ جایگزین می‌کند.
# قبل از اجرا حتماً مطمئن شوید که مسیر فایل درست است.
# ============================================================================
set -e

PROJECT_DIR="/opt/parseh_project"
BACKUP_FILE="$1"

if [ -z "${BACKUP_FILE}" ]; then
    echo "استفاده: bash restore_db.sh <مسیر فایل بک‌آپ.sql.gz>"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "خطا: فایل ${BACKUP_FILE} پیدا نشد."
    exit 1
fi

set -a
source "${PROJECT_DIR}/.env"
set +a

read -rp "⚠️  این کار دیتابیس فعلی '${DB_NAME}' را کاملاً پاک و جایگزین می‌کند. مطمئنید؟ (yes/no): " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
    echo "لغو شد."
    exit 0
fi

echo "[$(date)] متوقف کردن سرویس‌ها..."
sudo systemctl stop parseh parseh-celery parseh-celery-beat

echo "[$(date)] بازیابی دیتابیس از ${BACKUP_FILE}..."
gunzip -c "${BACKUP_FILE}" | PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST:-127.0.0.1}" -p "${DB_PORT:-5432}" -U "${DB_USER}" "${DB_NAME}"

echo "[$(date)] راه‌اندازی مجدد سرویس‌ها..."
sudo systemctl start parseh parseh-celery parseh-celery-beat

echo "[$(date)] بازیابی با موفقیت انجام شد."
