# CLAUDE.md — مغز پروژه پلتفرم املاک پارسه

> این فایل مرجع سریع پروژه برای Claude Code است. قبل از کار روی هر تسک، این فایل را بخوان؛
> نیازی به گشتن دستی در همه‌ی فایل‌ها نیست. اگر جایی این فایل با کد واقعی مغایرت داشت، کد واقعی درست است — این فایل را آپدیت کن.

## خلاصه یک‌خطی
پلتفرم کامل مدیریت/نمایش/خریدوفروش ملک با Django 5 + PostgreSQL + Redis/Celery + HTMX + Tailwind، شامل: سایت عمومی، سیستم کاربری، پنل اختصاصی مشاوران، پنل مدیریت مشاوران، گزارش‌گیری مدیر، و تحلیل هوشمند قیمت با DeepSeek AI.

## پشته فنی
| لایه | فناوری |
|---|---|
| بک‌اند | Django 5.1، Python 3.12 |
| دیتابیس | PostgreSQL (بدون PostGIS — قبلاً بود، حذف شد چون لازم نبود) |
| کش/صف | Redis + django-redis + Celery |
| فرانت | HTMX + Tailwind CSS (CDN، نه build فایل) — بدون React/Vue |
| نقشه | Leaflet + OpenStreetMap (رایگان، بدون API key) |
| AI | DeepSeek API از طریق کتابخانه `openai` |
| Auth | سیستم کاربری built-in جنگو (`django.contrib.auth`) + مدل `Profile` اضافه |
| استقرار | Nginx + Gunicorn + systemd، اسکریپت `setup.sh` |
| تست | Django TestCase، ۳۹ تست در `apps/*/tests.py` |

## ساختار اپ‌ها (به ترتیب اهمیت)

```
apps/
├── properties/   # هسته اصلی: مدل Property + لیست/جزئیات/فیلتر/نقشه/علاقه‌مندی/مقایسه/ارزیابی ملک
├── accounts/      # سیستم کاربری: Profile، ثبت‌نام/ورود/فراموشی رمز، ادغام session→account
├── advisor_panel/ # پنل مشاور (فقط ملک خودش) + پنل مدیریت مشاوران (فقط staff)
├── team/          # مدل TeamMember (مشاور) + صفحه عمومی معرفی مشاور
├── contact/       # فرم تماس + اعلان تلگرام
├── blog/          # مقالات
├── core/          # صفحه اصلی، درباره‌ما، FAQ، گزارش‌گیری مدیر (reports.py)، سیگنال کش
└── ai/            # سرویس DeepSeek برای تحلیل هوشمند ملک
```

## مدل‌های کلیدی (فیلد → اپ)

- **`Property`** (`apps.properties.models`) — ملک اصلی. فیلد `advisor` = FK به `TeamMember`. `save()` خودش slug می‌سازد + عکس‌ها را فشرده می‌کند (`compress_image_field`). دارای `Meta.indexes` روی `is_published+transaction_type`, `-created_at`, `price`, `-views_count`.
- **`Favorite`** — علاقه‌مندی کاربر واردشده (دیتابیس). برای مهمان از session استفاده می‌شود (کلید `favorite_properties`). منطق تشخیص در `apps/properties/wishlist_views.py` (`_favorite_ids`, `_is_favorite`).
- **`PropertyView`** — تاریخچه بازدید (فقط کاربر واردشده؛ `update_or_create` در `PropertyDetailView.get_object`).
- **`PropertyValuationRequest`** — درخواست ارزیابی آنلاین از مالکین (نه ملک ثبت‌شده). فیلد `assigned_advisor` نال‌پذیر.
- **`TeamMember`** (`apps.team.models`) — مشاور. فیلد `user` = OneToOne نال‌پذیر به `User`؛ اگر پر باشد یعنی آن یوزر می‌تواند وارد `/پنل-مشاور/` شود.
- **`Profile`** (`apps.accounts.models`) — OneToOne با `User`، فقط فیلد `phone`. با سیگنال `post_save` روی `User` خودکار ساخته می‌شود (`apps/accounts/signals.py`).
- **`ContactRequest`** — فیلد `user` نال‌پذیر (اگر واردشده باشد پر می‌شود)، فیلد `property` نال‌پذیر.
- **`FAQ`**, **`Post`** — ساده، بدون نکته خاص.

## قراردادهای مهم URL

- همه‌ی مسیرها **فارسی** هستند (`path("املاک/", ...)`), نه انگلیسی.
- اسلاگ ملک/مقاله فارسی است → از مبدل سفارشی `uslug` استفاده می‌شود (`config/converters.py`)، **نه** `slug` پیش‌فرض جنگو (چون regex پیش‌فرض فقط ASCII قبول می‌کند).
- مسیر ادمین قابل تنظیم است: `settings.ADMIN_URL` (env: `ADMIN_URL`)، پیش‌فرض `admin/` — **حتماً روی VPS واقعی عوضش کن**.
- `config/urls.py` نقطه ورود همه include هاست؛ ترتیب مسیرهای خاص باید همیشه **قبل از** الگوی عمومی `<uslug:slug>/` بیاید وگرنه catch-all اول از همه match می‌کند.

## الگوهای معماری مهم (قبل از تغییر دادن چیزی این‌ها را بخوان)

### ۱. CSRF برای دکمه‌های HTMX — این قبلاً یه باگ واقعی بود
هر `hx-post` که داخل `<form>` نباشد (مثل دکمه‌های لایک/مقایسه/تحلیل AI)، به‌صورت خودکار توکن CSRF نمی‌فرستد.
**راه‌حل که الان فعاله:** `templates/base.html` یک `{% csrf_token %}` بدون فرم در ابتدای `<body>` رندر می‌کند (تضمین ست‌شدن کوکی) + یک listener سراسری `htmx:configRequest` که هدر `X-CSRFToken` را از کوکی می‌خواند و به هر درخواست HTMX اضافه می‌کند. **این دو تکه را هرگز حذف نکن.**

### ۲. علاقه‌مندی: session (مهمان) در برابر دیتابیس (کاربر واردشده)
منطق در `apps/properties/wishlist_views.py`. توابع `_favorite_ids(request)` و `_is_favorite(request, property)` تشخیص خودکار می‌دهند. وقتی کاربر مهمان بعداً ثبت‌نام/ورود کند، `_merge_session_favorites_into_account` (در `apps/accounts/views.py`) علاقه‌مندی‌های session را به `Favorite` منتقل می‌کند. **مقایسه (Compare) همیشه فقط session است، حتی برای کاربر واردشده — عمدی است.**

### ۳. دسترسی پنل مشاور — امنیتی و تست‌شده
`apps/advisor_panel/mixins.py`:
- `AdvisorRequiredMixin` → کاربر باید `hasattr(user, 'team_member')` باشد یا `is_staff`. `get_queryset()` هر ویو باید فیلتر `advisor=self.get_advisor()` بزند وگرنه مشاور به ملک بقیه دسترسی پیدا می‌کند.
- `ManagerRequiredMixin` → فقط `is_staff` (برای `/پنل-مشاور/مدیریت-مشاوران/`).
- تست‌های `apps/advisor_panel/tests.py` دقیقاً همین جداسازی را چک می‌کنند — قبل از تغییر این ویوها تست‌ها را اجرا کن.

### ۴. فشرده‌سازی خودکار عکس + تبدیل به WebP
`apps/core/image_utils.py::compress_image_field()` — در `save()` مدل‌های `Property`, `TeamMember`, `Post`, `PropertyValuationRequest` صدا زده می‌شود. فقط فایل‌های **تازه‌آپلودشده** را پردازش می‌کند (چک `_committed` و `isinstance(..., UploadedFile)`) — هرگز فایل‌های قبلاً ذخیره‌شده را دوباره فشرده نمی‌کند (وگرنه کیفیت هر بار افت می‌کرد). خروجی همیشه **WebP** است (کیفیت ۸۲٪، حداکثر ۱۶۰۰px) صرف‌نظر از فرمت آپلودی (jpg/png/webp) — پسوند فایل ذخیره‌شده هم به `.webp` تغییر می‌کند. اعتبارسنجی پسوند آپلودی (`apps.core.validators.validate_image_file`) روی فایل **قبل از** این تبدیل چک می‌شود، پس تغییر نکرده.

### ۵. کش صفحه اصلی + صفحه جزئیات ملک + ابطال خودکار
`apps/core/views.py::HomeView` سه کوئری (`sale_properties`, `rent_properties`, `team_members`) و `apps/properties/views.py::PropertyDetailView` استخر ملک‌های مرتبط (`property_detail:related:sale` / `property_detail:related:rent`، ۱۰تای آخر هر نوع معامله) را ۱۵ دقیقه کش می‌کنند. `apps/core/signals.py` با `post_save`/`post_delete` روی `Property` و `TeamMember` همه‌ی این کلیدها را با هم پاک می‌کند. اگر مدل/کوئری جدیدی اضافه کردی که باید کش شود، هم کلید کش را در ویو اضافه کن هم به لیست `cache.delete_many` در `signals.py::_clear_home_cache` اضافه‌اش کن.
**نکته پایداری:** `CACHES.OPTIONS.IGNORE_EXCEPTIONS = True` در `config/settings/base.py` — اگر Redis پایین باشد سایت کرش نمی‌کند، فقط کش نادیده گرفته می‌شود.

### ۶. تسک‌های Celery باید دقیقاً `tasks.py` نام‌گذاری شوند
`autodiscover_tasks()` فقط دنبال فایل `tasks.py` در هر اپ می‌گردد (نه `valuation_tasks.py` یا اسم دیگر) وگرنه worker جدا اصلاً تسک را نمی‌شناسد. الان در `apps/ai/tasks.py`, `apps/contact/tasks.py`, `apps/properties/tasks.py`.

### ۷. بک‌آپ ابری خارج از سرور
`backup_db.sh` بعد از بک‌آپ محلی PostgreSQL، اگر `RCLONE_REMOTE` در `.env` تنظیم شده باشد (و `rclone` نصب باشد)، فایل را با `rclone copy` به فضای ابری هم آپلود می‌کند و نسخه‌های ابری قدیمی‌تر از ۳۰ روز را پاک می‌کند. اگر `RCLONE_REMOTE` خالی باشد یا `rclone` نصب نباشد، این مرحله بی‌سروصدا رد می‌شود و فقط بک‌آپ محلی (که همیشه اجرا می‌شود) معتبر می‌ماند. شکست آپلود ابری کد خروج ۲ برمی‌گرداند (نه ۱) تا از شکست بک‌آپ محلی قابل تشخیص باشد.

### ۸. اعلان تلگرام — سرویس مشترک
منطق پایه در `apps/core/telegram.py::send_telegram_message()`. هر اپ (`contact`, `properties`) یک wrapper نازک روی آن دارد (`telegram_notify.py` / `valuation_notify.py`) که پیام مخصوص خودش را می‌سازد. اگر می‌خواهی اعلان جدید اضافه کنی، تابع پایه را تغییر نده، فقط یک wrapper جدید بساز.

### ۹. رنگ/فونت برند — دیگر دست نزن مگر خواسته شود
پالت در `templates/base.html` (تگ `<style>` بالای فایل): `primary` #0E5D50 (سبز زیتونی)، `accent` #C68A3D (طلایی)، `brick` #B6512E، `canvas` #FAF6EF، `ink` #1B2A2E، `line` #E4DDD0. فونت فقط **Vazirmatn** (فونت نستعلیق/Aref Ruqaa عمداً حذف شد، کاربر نخواستش).
حالت تاریک از طریق CSS variables + کلاس `.dark` روی `<html>` پیاده‌سازی شده (نه `dark:` utility روی تک‌تک المان‌ها) — یعنی اکثر `bg-white`/`text-ink`/`border-line` خودکار دارک‌مود می‌گیرند بدون دست‌زدن به هر template.

## راه‌اندازی محیط توسعه محلی (این کپی روی لپ‌تاپ/سیستم `ni`)

این سیستم به `sudo`/`apt`/Docker دسترسی ندارد و ماژول `venv` استاندارد پایتون هم شکسته است (`ensurepip` نصب نیست) — پس روش معمول (`python -m venv venv`) کار نمی‌کند. راه‌حلی که الان جاافتاده:

```bash
mkdir -p .venv-libs
env -u PIP_PREFIX python3 -m pip install --target=.venv-libs -r requirements/development.txt
export PYTHONPATH=".venv-libs:$PYTHONPATH"
set -a && source .env && set +a
python3 manage.py test
```

- `.env` از روی `.env.example` ساخته شده با `DJANGO_SETTINGS_MODULE=config.settings.local_test` (نه `production`/`development`) و `DEBUG=True` — این ستینگ از `SQLite` استفاده می‌کند (`db.sqlite3`) چون PostgreSQL روی این سیستم نصب/در دسترس نیست.
- Redis هم در دسترس نیست؛ چون `CACHES.OPTIONS.IGNORE_EXCEPTIONS = True` است، سایت/تست‌ها بدون کرش کار می‌کنند (کش فقط نادیده گرفته می‌شود). Celery واقعی (`.delay()` روی broker واقعی) روی این سیستم تست نشده — برای تست تسک‌های async باید یا Redis واقعی جور شود یا موقتاً `CELERY_TASK_ALWAYS_EAGER=True` ست شود.
- **مهم:** فولدرهای `migrations/` قبل از این هیچ فایلی نداشتند (فقط `__init__.py` — در گیت‌ایگنور هم نبودند). در اولین راه‌اندازی با `makemigrations` تولید و با `migrate` اعمال شدند. اگر نسخه‌ی دیگری از پروژه (مثلاً روی VPS) migration های متفاوتی دارد، قبل از هر sync باید دستی مقایسه/merge شوند.
- بک‌آپ/ریستور (`backup_db.sh`/`restore_db.sh`) روی PostgreSQL نوشته شده‌اند و روی SQLite این محیط کاربردی ندارند.

### باگ‌هایی که در همین راه‌اندازی اول پیدا و رفع شدند
1. **`PropertyDetailView.get_queryset`** (`apps/properties/views.py`) فیلتر `is_published=True` نداشت → ملک منتشرنشده از طریق URL مستقیم برای همه (حتی کاربر مهمان) قابل دیدن بود. رفع شد با اضافه‌کردن `.filter(is_published=True)`.
2. **`make_test_image()`** (`apps/properties/tests.py`) یک PNG هاردکدشده با CRC نامعتبر داشت که باعث fail شدن `ImageField` در فرم‌ها می‌شد (نه باگ اپلیکیشن، فقط فیکسچر تست خراب بود). رفع شد: حالا با خود Pillow یک PNG واقعی می‌سازد.

## متغیرهای محیطی مهم (`.env`)
`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `ADMIN_URL`, `DB_*`, `REDIS_URL`, `RCLONE_REMOTE` (بک‌آپ ابری، اختیاری)، `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SITE_*`, `EMAIL_*` (برای فراموشی رمز واقعی). لیست کامل در `.env.example`.

تنظیمات سه‌لایه: `config/settings/base.py` (مشترک) → `development.py` (DEBUG=True, ایمیل کنسولی) → `production.py` (HSTS, لاگ فایل چرخشی، بررسی ALLOWED_HOSTS اجباری).

## دستورات ضروری

```bash
python manage.py makemigrations && python manage.py migrate   # بعد از هر تغییر مدل
python manage.py seed_data [--flush]                          # دیتای نمونه (۱۰ ملک واقعی با عکس دانلودی، ۵ مشاور، FAQ، وبلاگ)
python manage.py test                                         # ۳۹ تست؛ قبل از هر commit اجرا کن
python manage.py runserver
bash backup_db.sh                                              # بک‌آپ دستی دیتابیس (کران‌جاب هم برایش تنظیم شده، هر شب ۳ بامداد)
bash restore_db.sh backups/FILE.sql.gz                          # بازیابی از بک‌آپ (فقط در اضطرار)
```

## نکات قبل از هر تغییر

1. اگر مدل عوض شد → یادآوری بده که `makemigrations`/`migrate` لازم است (خودت اجرا نکن مگر خواسته شود).
2. اگر ویو/فرم جدید با `hx-post` ساختی که داخل `<form>` نیست → مطمئن شو global CSRF handler (بخش ۱ بالا) پوشش می‌دهد؛ نیازی به csrf_token دستی نیست.
3. اگر فیلد تصویر جدید اضافه کردی → `validators=[validate_image_file]` (از `apps.core.validators`) بگذار و در `save()` مدل `compress_image_field` صدا بزن.
4. قبل از تحویل نهایی هر تغییر، حداقل یک بار `python manage.py test` و `python manage.py check` را (اگر Django نصب است) اجرا کن.
5. متن‌ها/UI همیشه فارسی و راست‌چین (`dir="rtl"`) — این یک پروژه بین‌المللی نیست.
