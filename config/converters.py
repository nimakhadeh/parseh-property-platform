"""
مبدل مسیر سفارشی برای پشتیبانی از اسلاگ‌های یونیکد (فارسی).
مبدل پیش‌فرض جنگو (SlugConverter) فقط حروف انگلیسی/عدد را قبول می‌کند؛
چون اسلاگ‌های این پروژه با allow_unicode=True ساخته می‌شوند (فارسی هستند)،
باید از این مبدل سفارشی در urls.py استفاده شود.
"""


class UnicodeSlugConverter:
    # \w در حالت پیش‌فرض پایتون۳ حروف یونیکد (از جمله فارسی) را هم پوشش می‌دهد
    regex = r"[-\w]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value
