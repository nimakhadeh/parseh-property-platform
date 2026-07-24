from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from apps.core.validators import validate_image_file
from apps.core.image_utils import compress_image_field


class Post(models.Model):
    """مدل مقاله وبلاگ"""

    title = models.CharField("عنوان مقاله", max_length=200)
    slug = models.SlugField("اسلاگ", max_length=220, unique=True, blank=True, allow_unicode=True)
    content = models.TextField("متن مقاله")
    summary = models.CharField("خلاصه", max_length=300)
    image = models.ImageField("تصویر شاخص", upload_to="blog/", blank=True, null=True, validators=[validate_image_file])
    tags = models.CharField("برچسب‌ها (با ویرگول جدا کنید)", max_length=250, blank=True)
    is_published = models.BooleanField("منتشر شده", default=True)
    views_count = models.PositiveIntegerField("تعداد بازدید", default=0)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("تاریخ بروزرسانی", auto_now=True)

    class Meta:
        verbose_name = "مقاله"
        verbose_name_plural = "مقالات"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        self.image = compress_image_field(self.image)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:post_detail", kwargs={"slug": self.slug})

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]
