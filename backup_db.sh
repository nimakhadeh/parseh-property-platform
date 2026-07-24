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
RCLONE_KEEP_DAYS=30  # روی فضای ابری بیشتر از خود سرور نگه می‌داریم

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
# آپلود بک‌آپ به فضای ابری خارج از سرور اصلی
# اگر همه‌چیز روی خود همین سرور بماند و سرور از بین برود، بک‌آپ هم از بین می‌رود.
# فعال‌سازی: RCLONE_REMOTE را در .env تنظیم کن (مثلاً "arvan:parseh-backups")
# بعد از نصب و `rclone config` برای یک سرویس ابری (آروان/S3/...).
# اگر تنظیم نشده باشد یا rclone نصب نباشد، این بخش بی‌سروصدا رد می‌شود —
# بک‌آپ محلی که بالا انجام شد کامل معتبر است، این فقط لایه‌ی اضافه‌ی امنیت است.
# --------------------------------------------------------------------------
CLOUD_UPLOAD_FAILED=0

if [ -n "${RCLONE_REMOTE:-}" ]; then
    if command -v rclone >/dev/null 2>&1; then
        echo "[$(date)] آپلود بک‌آپ به فضای ابری (${RCLONE_REMOTE})..."
        if rclone copy "${BACKUP_FILE}" "${RCLONE_REMOTE}/"; then
            echo "[$(date)] آپلود ابری موفق بود."
            rclone delete --min-age "${RCLONE_KEEP_DAYS}d" "${RCLONE_REMOTE}/" 2>&1 || true
        else
            echo "[$(date)] هشدار: آپلود ابری شکست خورد! بک‌آپ محلی همچنان معتبر است اما نسخه‌ی خارج از سرور به‌روز نشد." >&2
            CLOUD_UPLOAD_FAILED=1
        fi
    else
        echo "[$(date)] هشدار: RCLONE_REMOTE تنظیم شده ولی دستور rclone نصب نیست. فقط بک‌آپ محلی انجام شد." >&2
        CLOUD_UPLOAD_FAILED=1
    fi
else
    echo "[$(date)] RCLONE_REMOTE تنظیم نشده — بک‌آپ ابری خارج از سرور غیرفعال است (فقط بک‌آپ محلی)."
fi

echo "[$(date)] بک‌آپ کامل شد."

if [ "${CLOUD_UPLOAD_FAILED}" -eq 1 ]; then
    exit 2
fi
