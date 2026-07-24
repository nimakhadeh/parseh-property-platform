from django.db import models


class FAQ(models.Model):
    """پرسش و پاسخ متداول"""

    CATEGORY_CHOICES = [
        ("general", "عمومی"),
        ("buying", "خرید"),
        ("renting", "اجاره"),
        ("legal", "حقوقی"),
        ("ai", "تحلیل هوشمند"),
    ]

    question = models.CharField("پرسش", max_length=300)
    answer = models.TextField("پاسخ")
    category = models.CharField("دسته‌بندی", max_length=20, choices=CATEGORY_CHOICES, default="general")
    order = models.PositiveIntegerField("ترتیب نمایش", default=0)
    is_published = models.BooleanField("منتشر شده", default=True)

    class Meta:
        verbose_name = "پرسش متداول"
        verbose_name_plural = "پرسش‌های متداول"
        ordering = ["category", "order"]

    def __str__(self):
        return self.question
