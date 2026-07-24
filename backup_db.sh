#!/usr/bin/env bash
# ============================================================================
# بک‌آپ خودکار روزانه‌ی دیتابیس پلتفرم املاک پارسه
# نصب:
#   sudo cp backup_db.sh /opt/parseh_project/backup_db.sh
#   sudo chmod +x /opt/parseh_project/backup_db.sh
#   sudo crontab -e
#   # این خط را اضافه کنید (هر شب ساعت ۳ بامداد):
#   0 3 * * * /opt/parseh_project/backup_db.sh >> /opt/parseh_project/logs/backup.log 2>&1
# ============================================================================
set -e

PROJECT_DIR="/opt/parseh_project"
BACKUP_DIR="${PROJECT_DIR}/backups"
DATE=$(date +%Y-%m-%d_%H-%M)
KEEP_DAYS=14  # نگه‌داری بک‌آپ‌ها تا ۱۴ روز، قدیمی‌تر خودکار پاک می‌شود

# خواندن متغیرهای دیتابیس از .env
set -a
source "${PROJECT_DIR}/.env"
set +a

mkdir -p "${BACKUP_DIR}"

BACKUP_FILE="${BACKUP_DIR}/parseh_db_${DATE}.sql.gz"

echo "[$(date)] شروع بک‌آپ دیتابیس..."
PGPASSWORD="${DB_PASSWORD}" pg_dump -h "${DB_HOST:-127.0.0.1}" -p "${DB_PORT:-5432}" -U "${DB_USER}" "${DB_NAME}" | gzip > "${BACKUP_FILE}"

if [ -s "${BACKUP_FILE}" ]; then
    echo "[$(date)] بک‌آپ با موفقیت ذخیره شد: ${BACKUP_FILE} ($(du -h "${BACKUP_FILE}" | cut -f1))"
else
    echo "[$(date)] خطا: فایل بک‌آپ خالی است!"
    exit 1
fi

# پاک‌سازی بک‌آپ‌های قدیمی‌تر از KEEP_DAYS روز
find "${BACKUP_DIR}" -name "parseh_db_*.sql.gz" -mtime +${KEEP_DAYS} -delete
echo "[$(date)] بک‌آپ‌های قدیمی‌تر از ${KEEP_DAYS} روز پاک شدند."

# --------------------------------------------------------------------------
# (اختیاری ولی به‌شدت پیشنهادی) آپلود بک‌آپ به فضای ابری خارج از سرور اصلی
# اگر همه‌چیز روی خود همین سرور بماند و سرور از بین برود، بک‌آپ هم از بین می‌رود.
# نمونه با rclone (بعد از نصب و کانفیگ rclone برای یک سرویس ابری مثل آروان/S3):
#
# rclone copy "${BACKUP_FILE}" remote:parseh-backups/
# --------------------------------------------------------------------------

echo "[$(date)] بک‌آپ کامل شد."
