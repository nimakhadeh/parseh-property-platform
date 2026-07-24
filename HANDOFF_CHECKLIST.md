# چک‌لیست قبل از شروع کار با Claude Code

## ۱. تایید سلامت پروژه (اینجا فقط تحلیل ایستا انجام شد، نه اجرای واقعی)
```bash
cd /path/to/parseh_project
source venv/bin/activate
set -a && source .env && set +a

python manage.py check          # باید بدون خطا تمام شود
python manage.py makemigrations # باید همه‌چیز sync باشد یا مایگریشن جدید بسازد
python manage.py migrate
python manage.py test           # همه‌ی ۳۹ تست باید سبز شوند
```
اگر هرکدام از این‌ها fail شد، **این اولین چیزیه که باید با Claude Code حل کنی**، قبل از هر فیچر جدید.

## ۲. فایل‌های راهنما سر جایشان هستند؟
- [ ] `CLAUDE.md` در ریشه پروژه
- [ ] `.claude/settings.json`
- [ ] `.claude/commands/pre-deploy.md`
- [ ] `.claude/commands/new-model-field.md`
- [ ] `backup_db.sh` و `restore_db.sh` در ریشه پروژه (و اجراپذیر: `chmod +x`)

## ۳. بک‌آپ رو یک‌بار دستی امتحان کن
```bash
sudo bash backup_db.sh
ls -lh backups/
```
یک بار هم بازیابی را روی یک دیتابیس تستی امتحان کن تا مطمئن شوی در روز مبادا واقعاً کار می‌کند.

## ۴. کران‌جاب بک‌آپ را فعال کن
```bash
sudo crontab -e
# اضافه کن:
0 3 * * * /opt/parseh_project/backup_db.sh >> /opt/parseh_project/logs/backup.log 2>&1
```

## ۵. اولین دستوری که به Claude Code می‌دهی
پیشنهاد می‌کنم اولین پیام به Claude Code دقیقاً این باشد:

> «فایل CLAUDE.md رو بخون تا با پروژه آشنا بشی. بعد `python manage.py test` رو اجرا کن و مطمئن شو
> همه‌چیز سبزه. اگه چیزی fail شد بهم بگو، فیچر جدید شروع نکن.»

این‌طوری قبل از هر کاری، Claude Code با یه پایه‌ی تاییدشده و واقعی (نه فقط تحلیل ایستا) شروع می‌کنه.

## ۶. بعد از آن، به ترتیب اولویت برو سراغ:
1. بک‌آپ ابری خارج از سرور (rclone به یک فضای ابری) — چون بک‌آپ روی خود سرور کافی نیست
2. کش صفحه جزئیات ملک + تبدیل عکس به WebP
3. یکی از فیچرهای خفن (مقایسه محله‌ای یا تور ۳۶۰) — با Claude Code، چون نیاز به تست تعاملی زیاد دارد
