"""
نقشه سایت (Sitemap) برای بهبود سئو و کمک به موتورهای جستجو در ایندکس‌کردن صفحات.
آدرس نهایی: /sitemap.xml
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.properties.models import Property
from apps.blog.models import Post


class PropertySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Property.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


class PostSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Post.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return ["core:home", "core:about", "core:faq", "properties:property_list", "properties:valuation_request", "blog:post_list", "contact:contact_page"]

    def location(self, item):
        return reverse(item)


sitemaps = {
    "properties": PropertySitemap,
    "blog": PostSitemap,
    "static": StaticViewSitemap,
}
