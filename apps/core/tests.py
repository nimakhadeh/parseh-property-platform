from django.test import RequestFactory, SimpleTestCase, override_settings
from django.core.cache import cache
from django_ratelimit.core import get_usage


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class ProxyRateLimitTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def usage(self, remote, real_ip):
        request = RequestFactory().post("/", REMOTE_ADDR=remote, HTTP_X_REAL_IP=real_ip)
        return get_usage(request, group="proxy-regression", key="ip", rate="1/h", method="POST", increment=True)

    def test_unix_socket_uses_nginx_client_ip_and_separates_visitors(self):
        self.assertFalse(self.usage("", "203.0.113.1")["should_limit"])
        self.assertTrue(self.usage("", "203.0.113.1")["should_limit"])
        self.assertFalse(self.usage("", "203.0.113.2")["should_limit"])

    def test_tcp_peer_cannot_bypass_limit_with_forwarded_header(self):
        self.assertFalse(self.usage("203.0.113.1", "192.0.2.1")["should_limit"])
        self.assertTrue(self.usage("203.0.113.1", "192.0.2.2")["should_limit"])
