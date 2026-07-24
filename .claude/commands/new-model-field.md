در حال افزودن یک فیلد یا مدل جدید به پروژه هستیم. طبق CLAUDE.md این موارد را رعایت کن:

- اگر فیلد از نوع ImageField است: `validators=[validate_image_file]` (از `apps.core.validators`) اضافه کن و در متد `save()` مدل، `compress_image_field` (از `apps.core.image_utils`) را روی آن صدا بزن.
- اگر مدل باید در صفحه اصلی نمایش داده شود: کوئری‌اش را در `HomeView` کش کن و سیگنال ابطال کش متناظر را در `apps/core/signals.py` اضافه کن.
- اگر فیلد مربوط به شماره تماس است: از `phone_validator` (الگوی regex موجود در `apps/contact/models.py` یا `apps/accounts/models.py`) استفاده کن، دوباره از صفر ننویس.
- بعد از افزودن، به من یادآوری کن که `python manage.py makemigrations` و `migrate` لازم است.
- اگر این تغییر باعث می‌شود بخشی از CLAUDE.md قدیمی/نادرست شود، آن بخش را پیشنهاد بده که آپدیت شود.
