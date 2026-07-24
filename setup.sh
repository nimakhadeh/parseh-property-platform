#!/usr/bin/env bash
# ============================================================================
# اسکریپت نصب خودکار پلتفرم املاک پارسه روی سرور Ubuntu 22.04 / 24.04
# استفاده:  sudo bash setup.sh
# فرض بر این است که این اسکریپت کنار پوشه‌ی کامل پروژه اجرا می‌شود.
# ============================================================================
set -e

PROJECT_NAME="parseh_project"
PROJECT_DIR="/opt/${PROJECT_NAME}"
DB_NAME="parseh_db"
DB_USER="parseh_user"
DOMAIN=""

info()    { echo -e "\e[32m[اطلاعات]\e[0m $1"; }
warn()    { echo -e "\e[33m[هشدار]\e[0m $1"; }
error()   { echo -e "\e[31m[خطا]\e[0m $1"; exit 1; }

if [[ $EUID -ne 0 ]]; then
    error "این اسکریپت باید با دسترسی root یا sudo اجرا شود. مثال: sudo bash setup.sh"
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ----------------------------------------------------------------------------
# ۱) نصب بسته‌های سیستمی
# ----------------------------------------------------------------------------
info "بروزرسانی مخازن و نصب بسته‌های سیستمی مورد نیاز..."
apt-get update -y
apt-get install -y \
    python3.12 python3.12-venv python3-pip \
    postgresql postgresql-contrib \
    libpq-dev binutils \
    redis-server nginx git curl build-essential

# ----------------------------------------------------------------------------
# ۲) راه‌اندازی و فعال‌سازی PostgreSQL و Redis
# ----------------------------------------------------------------------------
info "فعال‌سازی سرویس‌های PostgreSQL و Redis..."
systemctl enable --now postgresql
systemctl enable --now redis-server

# ----------------------------------------------------------------------------
# ۳) ایجاد کاربر و دیتابیس PostGIS
# ----------------------------------------------------------------------------
info "ایجاد کاربر و دیتابیس PostgreSQL با پشتیبانی PostGIS..."
DB_PASSWORD=$(openssl rand -hex 16)

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

# ----------------------------------------------------------------------------
# ۴) کپی پروژه در /opt/parseh_project
# ----------------------------------------------------------------------------
info "کپی فایل‌های پروژه به ${PROJECT_DIR}..."
mkdir -p "${PROJECT_DIR}"
rsync -a --exclude 'venv' --exclude '.git' --exclude '__pycache__' "${SOURCE_DIR}/" "${PROJECT_DIR}/"
mkdir -p "${PROJECT_DIR}/run" "${PROJECT_DIR}/logs" "${PROJECT_DIR}/media" "${PROJECT_DIR}/staticfiles"

# ----------------------------------------------------------------------------
# ۵) تنظیم فایل .env
# ----------------------------------------------------------------------------
if [[ ! -f "${PROJECT_DIR}/.env" ]]; then
    info "ایجاد فایل .env با مقادیر پیش‌فرض..."
    SECRET_KEY=$(openssl rand -hex 32)
    read -rp "دامنه یا IP سرور خود را وارد کنید (مثلاً example.com یا 1.2.3.4): " DOMAIN
    DOMAIN=${DOMAIN:-localhost}

    cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
    sed -i "s|SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|" "${PROJECT_DIR}/.env"
    sed -i "s|ALLOWED_HOSTS=.*|ALLOWED_HOSTS=${DOMAIN},localhost,127.0.0.1|" "${PROJECT_DIR}/.env"
    sed -i "s|DB_NAME=.*|DB_NAME=${DB_NAME}|" "${PROJECT_DIR}/.env"
    sed -i "s|DB_USER=.*|DB_USER=${DB_USER}|" "${PROJECT_DIR}/.env"
    sed -i "s|DB_PASSWORD=.*|DB_PASSWORD=${DB_PASSWORD}|" "${PROJECT_DIR}/.env"

    warn "فایل .env با مقادیر پیش‌فرض ساخته شد. لطفاً بعداً مقدار DEEPSEEK_API_KEY و سایر تنظیمات دلخواه را در ${PROJECT_DIR}/.env ویرایش کنید."
else
    info "فایل .env از قبل موجود است؛ از مقادیر فعلی استفاده می‌شود."
fi

# ----------------------------------------------------------------------------
# ۶) ساخت محیط مجازی و نصب وابستگی‌ها
# ----------------------------------------------------------------------------
info "ساخت محیط مجازی پایتون و نصب وابستگی‌ها..."
cd "${PROJECT_DIR}"
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements/production.txt
deactivate

# ----------------------------------------------------------------------------
# ۷) اجرای migrate و collectstatic
# ----------------------------------------------------------------------------
info "اجرای migrate و collectstatic..."
set -a
source "${PROJECT_DIR}/.env"
set +a

"${PROJECT_DIR}/venv/bin/python" manage.py migrate --noinput
"${PROJECT_DIR}/venv/bin/python" manage.py collectstatic --noinput

info "برای ساخت کاربر مدیر (superuser)، بعد از پایان اسکریپت دستور زیر را اجرا کنید:"
echo "  cd ${PROJECT_DIR} && source venv/bin/activate && python manage.py createsuperuser"

# ----------------------------------------------------------------------------
# ۸) مالکیت فایل‌ها برای کاربر www-data
# ----------------------------------------------------------------------------
chown -R www-data:www-data "${PROJECT_DIR}"

# ----------------------------------------------------------------------------
# ۹) کپی و فعال‌سازی فایل‌های systemd
# ----------------------------------------------------------------------------
info "نصب سرویس‌های systemd..."
cp "${PROJECT_DIR}/parseh.service" /etc/systemd/system/parseh.service
cp "${PROJECT_DIR}/parseh-celery.service" /etc/systemd/system/parseh-celery.service
cp "${PROJECT_DIR}/parseh-celery-beat.service" /etc/systemd/system/parseh-celery-beat.service

systemctl daemon-reload
systemctl enable --now parseh.service
systemctl enable --now parseh-celery.service
systemctl enable --now parseh-celery-beat.service

# ----------------------------------------------------------------------------
# ۱۰) تنظیم Nginx
# ----------------------------------------------------------------------------
info "تنظیم Nginx..."
NGINX_CONF="/etc/nginx/sites-available/parseh"
cp "${PROJECT_DIR}/nginx.conf" "${NGINX_CONF}"
if [[ -n "${DOMAIN}" && "${DOMAIN}" != "localhost" ]]; then
    sed -i "s/server_name example.com www.example.com;/server_name ${DOMAIN};/" "${NGINX_CONF}"
fi
ln -sf "${NGINX_CONF}" /etc/nginx/sites-enabled/parseh
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx

# ----------------------------------------------------------------------------
# ۱۱) پیشنهاد فعال‌سازی SSL با Certbot
# ----------------------------------------------------------------------------
echo
read -rp "آیا مایلید SSL رایگان با Certbot (Let's Encrypt) فعال شود؟ [y/N]: " ENABLE_SSL
if [[ "${ENABLE_SSL}" =~ ^[Yy]$ ]]; then
    apt-get install -y certbot python3-certbot-nginx
    certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m "admin@${DOMAIN}" || \
        warn "فعال‌سازی SSL ناموفق بود؛ می‌توانید بعداً دستی اجرا کنید: certbot --nginx -d ${DOMAIN}"
fi

# ----------------------------------------------------------------------------
# پایان
# ----------------------------------------------------------------------------
echo
info "نصب با موفقیت به پایان رسید! ✅"
echo "  آدرس پروژه: http://${DOMAIN}"
echo "  مسیر پروژه: ${PROJECT_DIR}"
echo "  فایل env:   ${PROJECT_DIR}/.env"
echo
info "برای بررسی وضعیت سرویس‌ها:"
echo "  systemctl status parseh"
echo "  systemctl status parseh-celery"
echo "  systemctl status parseh-celery-beat"
