"""
دستور مدیریتی برای پر کردن دیتابیس با دیتای نمونه (تست).
اجرا: python manage.py seed_data
برای پاک‌سازی کامل قبل از ورود دیتای جدید: python manage.py seed_data --flush
"""
import random
import logging
from io import BytesIO

import requests
from PIL import Image, ImageDraw
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.team.models import TeamMember
from apps.properties.models import Property
from apps.blog.models import Post
from apps.contact.models import ContactRequest
from apps.core.models import FAQ

logger = logging.getLogger(__name__)


def download_image(url, filename, timeout=10):
    """
    دانلود یک تصویر از اینترنت و برگرداندن آن به شکل ContentFile قابل ذخیره در ImageField.
    اگر اینترنت در دسترس نباشد یا دانلود ناموفق باشد، None برمی‌گرداند (بدون کرش کردن دستور).
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return ContentFile(response.content, name=filename)
    except requests.RequestException as exc:
        logger.warning("دانلود تصویر %s ناموفق بود: %s", url, exc)
        return None


def placeholder_image(filename, size=(900, 600)):
    """
    وقتی دانلود تصویر واقعی ناموفق باشد (مثلاً بدون اینترنت)، یک تصویر جایگزین برندی
    (گرادیانت هم‌رنگ پالت سایت + آیکون ساده‌ی خانه) می‌سازد، تا هم seed_data کرش نکند
    و هم به‌جای یک مربع خاکستری تخت و یکنواخت، ظاهر قابل‌قبول‌تری داشته باشد.
    """
    width, height = size
    top, bottom = (232, 242, 239), (250, 246, 239)  # primary-light -> canvas (برند سایت)
    gradient = Image.new("RGB", (1, height))
    for y in range(height):
        ratio = y / max(height - 1, 1)
        gradient.putpixel((0, y), tuple(
            round(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3)
        ))
    img = gradient.resize((width, height))

    draw = ImageDraw.Draw(img)
    primary = (14, 93, 80)
    cx, cy, s = width // 2, height // 2, min(width, height) // 6
    draw.polygon(
        [(cx - s, cy - s // 4), (cx, cy - int(s * 1.3)), (cx + s, cy - s // 4)],
        outline=primary, width=4,
    )
    draw.rectangle(
        [(cx - int(s * 0.7), cy - s // 4), (cx + int(s * 0.7), cy + s)],
        outline=primary, width=4,
    )

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=80)
    return ContentFile(buffer.getvalue(), name=filename)


ADVISORS = [
    {
        "name": "نیما خاده",
        "role": "rent",
        "bio": "مشاور برتر بخش اجاره با بیش از ۸ سال تجربه در معاملات ملکی منطقه تهران.",
        "phone": "0912-000-0001",
        "email": "nima.khadeh@parseh-estate.ir",
    },
    {
        "name": "زهرا ماندگاری",
        "role": "sale",
        "bio": "مشاور برتر بخش فروش، متخصص در معاملات آپارتمان‌های لوکس و پروژه‌های سرمایه‌گذاری.",
        "phone": "0912-000-0002",
        "email": "zahra.mandegari@parseh-estate.ir",
    },
    {
        "name": "علی رستمی",
        "role": "investment",
        "bio": "مشاور سرمایه‌گذاری با تمرکز بر تحلیل بازده و رشد ارزش ملک.",
        "phone": "0912-000-0003",
        "email": "ali.rostami@parseh-estate.ir",
    },
    {
        "name": "سارا احمدی",
        "role": "legal",
        "bio": "مشاور حقوقی با تخصص در تنظیم قراردادها و امور ثبتی ملک.",
        "phone": "0912-000-0004",
        "email": "sara.ahmadi@parseh-estate.ir",
    },
    {
        "name": "محمد کریمی",
        "role": "manager",
        "bio": "مدیر مجموعه پارسه با بیش از ۱۵ سال سابقه در صنعت املاک.",
        "phone": "0912-000-0005",
        "email": "mohammad.karimi@parseh-estate.ir",
    },
]

DISTRICTS = [
    "ولنجک", "زعفرانیه", "الهیه", "سعادت‌آباد", "فرمانیه",
    "نیاوران", "پاسداران", "جردن", "اقدسیه", "شهرک غرب",
]

PROPERTY_TITLES_SALE = [
    "آپارتمان لوکس نوساز", "پنت‌هاوس مدرن با تراس", "واحد دوبلکس دلباز",
    "آپارتمان تک‌واحدی خوش‌نقشه", "سوییت مبله شیک", "واحد نوساز با ویو کوهستان",
]

PROPERTY_TITLES_RENT = [
    "آپارتمان اجاره‌ای مبله", "واحد اداری-مسکونی", "سوییت کوتاه‌مدت",
    "آپارتمان خانوادگی بازسازی‌شده", "واحد نوساز فول‌امکانات",
]

BLOG_POSTS = [
    {
        "title": "۷ نکته کلیدی قبل از خرید آپارتمان در تهران",
        "summary": "راهنمای کامل برای خریداران اولین ملک؛ از بررسی سند تا انتخاب منطقه مناسب.",
        "tags": "خرید ملک, راهنما, سرمایه‌گذاری",
    },
    {
        "title": "روند قیمت مسکن در نیمه دوم امسال چگونه خواهد بود؟",
        "summary": "تحلیل کارشناسان پارسه از عوامل موثر بر نوسانات بازار مسکن.",
        "tags": "بازار مسکن, تحلیل قیمت",
    },
    {
        "title": "تفاوت اجاره کوتاه‌مدت و بلندمدت؛ کدام برای شما مناسب‌تر است؟",
        "summary": "بررسی مزایا و معایب هر دو نوع قرارداد اجاره برای مستاجرین و موجرین.",
        "tags": "اجاره, قرارداد",
    },
    {
        "title": "چک‌لیست کامل بازدید حضوری از ملک",
        "summary": "چه نکاتی را در بازدید حضوری از یک واحد مسکونی نباید فراموش کنید؟",
        "tags": "بازدید ملک, راهنما",
    },
]

CONTACT_MESSAGES = [
    {"name": "حسین یزدانی", "phone": "09121234567", "message": "سلام، برای بازدید از یکی از واحدهای فروش وقت می‌خواستم."},
    {"name": "مریم صادقی", "phone": "09359876543", "message": "درباره شرایط اجاره واحدهای مبله سوال داشتم."},
    {"name": "رضا قاسمی", "phone": "09121112233", "message": "لطفاً برای مشاوره سرمایه‌گذاری با من تماس بگیرید."},
]

FAQS = [
    {"question": "برای بازدید از ملک چطور وقت بگیرم؟", "answer": "از صفحه هر ملک روی «درخواست بازدید» بزنید یا با شماره درج‌شده در صفحه تماس با ما تماس بگیرید.", "category": "general"},
    {"question": "آیا پارسه در کل تهران فعالیت می‌کند؟", "answer": "بله، مشاوران ما در اکثر مناطق تهران با شما همکاری می‌کنند.", "category": "general"},
    {"question": "مدارک لازم برای خرید ملک چیست؟", "answer": "کارت ملی، شناسنامه و در صورت وام، مدارک بانکی مربوطه لازم است. مشاور حقوقی ما در تمام مراحل همراه شماست.", "category": "buying"},
    {"question": "هزینه کمیسیون خرید ملک چقدر است؟", "answer": "کمیسیون طبق نرخ مصوب اتحادیه املاک و معمولاً ۰.۵ درصد از طرفین معامله دریافت می‌شود.", "category": "buying"},
    {"question": "برای اجاره ملک چه ودیعه‌ای لازم است؟", "answer": "ودیعه بسته به منطقه و نوع ملک متفاوت است؛ جزئیات دقیق در صفحه هر ملک درج شده است.", "category": "renting"},
    {"question": "آیا امکان تبدیل ودیعه به اجاره وجود دارد؟", "answer": "بله، در بسیاری از موارد موجر با تبدیل بخشی از ودیعه به اجاره ماهانه موافقت می‌کند؛ از مشاور مربوطه بپرسید.", "category": "renting"},
    {"question": "قرارداد اجاره چقدر اعتبار قانونی دارد؟", "answer": "قراردادهای تنظیم‌شده توسط پارسه مطابق قوانین موجر و مستاجر تنظیم می‌شوند و از نظر حقوقی معتبرند.", "category": "legal"},
    {"question": "آیا سند ملک‌ها استعلام می‌شود؟", "answer": "بله، پیش از هر معامله، استعلام کامل سند و بدهی‌های احتمالی توسط تیم حقوقی پارسه انجام می‌شود.", "category": "legal"},
    {"question": "تحلیل هوشمند ملک چگونه کار می‌کند؟", "answer": "با کلیک روی دکمه «تحلیل هوشمند» در صفحه ملک، هوش مصنوعی بر اساس مشخصات ملک، مزایا، معایب و بازه قیمت پیشنهادی را ارائه می‌دهد.", "category": "ai"},
    {"question": "آیا تحلیل هوشمند رایگان است؟", "answer": "بله، اما برای جلوگیری از سوءاستفاده، هر کاربر در ساعت محدود به تعداد مشخصی درخواست تحلیل است.", "category": "ai"},
]


class Command(BaseCommand):
    help = "دیتابیس را با دیتای نمونه (مشاوران، املاک، مقالات، درخواست‌های تماس) پر می‌کند."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="قبل از ورود دیتای جدید، دیتای قبلی این مدل‌ها را پاک می‌کند.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write(self.style.WARNING("در حال پاک‌سازی دیتای قبلی..."))
            ContactRequest.objects.all().delete()
            Property.objects.all().delete()
            Post.objects.all().delete()
            TeamMember.objects.all().delete()
            FAQ.objects.all().delete()

        # ---------------------------------------------------------------
        # مشاوران
        # ---------------------------------------------------------------
        self.stdout.write("در حال ایجاد مشاوران...")
        advisor_objs = []
        for i, data in enumerate(ADVISORS):
            defaults = {
                "role": data["role"],
                "bio": data["bio"],
                "phone": data["phone"],
                "email": data["email"],
                "order": i,
                "is_active": True,
            }
            avatar_file = download_image(f"https://i.pravatar.cc/300?img={i + 12}", f"advisor-{i}.jpg")
            if avatar_file:
                defaults["image"] = avatar_file
            obj, created = TeamMember.objects.get_or_create(name=data["name"], defaults=defaults)
            advisor_objs.append(obj)
        self.stdout.write(self.style.SUCCESS(f"  {len(advisor_objs)} مشاور آماده شد."))

        rent_advisor = TeamMember.objects.filter(name="نیما خاده").first()
        sale_advisor = TeamMember.objects.filter(name="زهرا ماندگاری").first()

        # ---------------------------------------------------------------
        # املاک (۱۰ عدد؛ ۵ فروش با مشاور زهرا، ۵ اجاره با مشاور نیما)
        # ---------------------------------------------------------------
        self.stdout.write("در حال ایجاد املاک...")
        created_count = 0

        for i in range(5):
            district = random.choice(DISTRICTS)
            title = f"{random.choice(PROPERTY_TITLES_SALE)} در {district}"
            price = random.randint(35, 120) * 100_000_000  # بین ۳.۵ تا ۱۲ میلیارد
            image_seed = f"parseh-sale-{i}"
            defaults = {
                "description": (
                    f"این ملک واقع در منطقه {district} با دسترسی عالی به مراکز خرید و حمل‌ونقل عمومی، "
                    "گزینه‌ای مناسب برای سکونت یا سرمایه‌گذاری است. نور و تهویه مناسب، نمای مدرن و "
                    "مصالح باکیفیت از ویژگی‌های این واحد است."
                ),
                "price": price,
                "transaction_type": "sale",
                "area": random.randint(85, 240),
                "rooms": random.randint(2, 4),
                "floor": random.randint(1, 10),
                "total_floors": random.randint(6, 15),
                "year_built": random.randint(1398, 1404),
                "has_elevator": random.choice([True, True, False]),
                "has_parking": random.choice([True, True, False]),
                "has_warehouse": random.choice([True, False]),
                "has_balcony": random.choice([True, True, False]),
                "address": f"تهران، {district}، خیابان اصلی، پلاک {random.randint(1, 200)}",
                "advisor": sale_advisor,
                "is_published": True,
                "is_featured": (i == 0),
            }
            image_file = download_image(f"https://picsum.photos/seed/{image_seed}/900/600", f"{image_seed}.jpg")
            defaults["image"] = image_file or placeholder_image(f"{image_seed}.jpg")
            Property.objects.get_or_create(title=title, defaults=defaults)
            created_count += 1

        for i in range(5):
            district = random.choice(DISTRICTS)
            title = f"{random.choice(PROPERTY_TITLES_RENT)} در {district}"
            price = random.randint(20, 90) * 1_000_000  # ودیعه/اجاره نمونه
            image_seed = f"parseh-rent-{i}"
            defaults = {
                "description": (
                    f"واحد اجاره‌ای در {district}، مناسب برای زوج‌های جوان یا افراد شاغل در مرکز شهر. "
                    "دسترسی راحت به مترو و اتوبوس، نزدیک به فروشگاه‌ها و مراکز درمانی."
                ),
                "price": price,
                "transaction_type": "rent",
                "area": random.randint(55, 150),
                "rooms": random.randint(1, 3),
                "floor": random.randint(1, 8),
                "total_floors": random.randint(4, 12),
                "year_built": random.randint(1395, 1404),
                "has_elevator": random.choice([True, False]),
                "has_parking": random.choice([True, False]),
                "has_warehouse": random.choice([True, False]),
                "has_balcony": random.choice([True, True, False]),
                "address": f"تهران، {district}، کوچه فرعی، پلاک {random.randint(1, 200)}",
                "advisor": rent_advisor,
                "is_published": True,
                "is_featured": (i == 0),
            }
            image_file = download_image(f"https://picsum.photos/seed/{image_seed}/900/600", f"{image_seed}.jpg")
            defaults["image"] = image_file or placeholder_image(f"{image_seed}.jpg")
            Property.objects.get_or_create(title=title, defaults=defaults)
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"  {created_count} ملک آماده شد (۵ فروش با زهرا ماندگاری / ۵ اجاره با نیما خاده)."))

        # ---------------------------------------------------------------
        # مقالات وبلاگ
        # ---------------------------------------------------------------
        self.stdout.write("در حال ایجاد مقالات وبلاگ...")
        for i, post_data in enumerate(BLOG_POSTS):
            defaults = {
                "summary": post_data["summary"],
                "content": (
                    f"{post_data['summary']}\n\n"
                    "در این مقاله به بررسی جوانب مختلف موضوع می‌پردازیم و راهکارهای عملی برای "
                    "تصمیم‌گیری بهتر ارائه می‌دهیم. تیم کارشناسی پارسه همواره در کنار شماست تا "
                    "بهترین انتخاب را برای نیازهای ملکی خود داشته باشید.\n\n"
                    "برای دریافت مشاوره تخصصی رایگان، همین امروز با ما تماس بگیرید."
                ),
                "tags": post_data["tags"],
                "is_published": True,
            }
            image_seed = f"parseh-blog-{i}"
            image_file = download_image(f"https://picsum.photos/seed/{image_seed}/900/500", f"{image_seed}.jpg")
            if image_file:
                defaults["image"] = image_file
            Post.objects.get_or_create(title=post_data["title"], defaults=defaults)
        self.stdout.write(self.style.SUCCESS(f"  {len(BLOG_POSTS)} مقاله آماده شد."))

        # ---------------------------------------------------------------
        # درخواست‌های تماس نمونه
        # ---------------------------------------------------------------
        self.stdout.write("در حال ایجاد درخواست‌های تماس...")
        sample_property = Property.objects.first()
        for msg_data in CONTACT_MESSAGES:
            ContactRequest.objects.get_or_create(
                name=msg_data["name"],
                phone=msg_data["phone"],
                defaults={
                    "message": msg_data["message"],
                    "property": sample_property,
                    "is_read": False,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"  {len(CONTACT_MESSAGES)} درخواست تماس آماده شد."))

        # ---------------------------------------------------------------
        # پرسش‌های متداول
        # ---------------------------------------------------------------
        self.stdout.write("در حال ایجاد پرسش‌های متداول...")
        for i, faq_data in enumerate(FAQS):
            FAQ.objects.get_or_create(
                question=faq_data["question"],
                defaults={
                    "answer": faq_data["answer"],
                    "category": faq_data["category"],
                    "order": i,
                    "is_published": True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"  {len(FAQS)} پرسش متداول آماده شد."))


        self.stdout.write(self.style.SUCCESS("\n✅ دیتای نمونه با موفقیت وارد شد!"))
        self.stdout.write("برای مشاهده به http://127.0.0.1:8000/ مراجعه کنید.")
