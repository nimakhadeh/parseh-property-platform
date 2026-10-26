"""رگرسیون انتقال امن دادهٔ نقشه و بازخورد فرم ارزیابی."""
import json
from decimal import Decimal
from html.parser import HTMLParser
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .models import Property, PropertyValuationRequest
from .valuation_views import ValuationRequestCreateView


class ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.json_scripts = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type") == "application/json":
            self.current = []

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.json_scripts.append("".join(self.current))
            self.current = None


class MapTemplateTests(SimpleTestCase):
    def test_titles_and_prices_are_json_data_even_with_script_delimiters(self):
        title = 'آپارتمان "پارسه" </script><img src=x onerror=alert(1)>'
        property_obj = Property(
            title=title, slug="test-property", price=5_000_000_000,
            latitude=Decimal("35.712300"), longitude=Decimal("51.404300"),
        )
        html = render_to_string(
            "properties/partials/map.html",
            {"properties": [property_obj], "map_id": "test-map"},
        )
        parser = ScriptParser()
        parser.feed(html)
        self.assertEqual(len(parser.json_scripts), 1)
        points = json.loads(parser.json_scripts[0])
        self.assertEqual(points[0]["title"], title)
        self.assertEqual(points[0]["price"], "5.0 میلیارد تومان")
        self.assertEqual(points[0]["lat"], 35.7123)
        self.assertEqual(points[0]["lng"], 51.4043)
        self.assertEqual(points[0]["url"], property_obj.get_absolute_url())
        self.assertNotIn("</script><img", html)


@override_settings(RATELIMIT_ENABLE=False)
class ValuationFeedbackTests(TestCase):
    def setUp(self):
        self.data = {
            "name": "مالک تست", "phone": "09121234567",
            "transaction_type": "sale", "address": "تهران",
        }

    @patch("apps.properties.tasks.notify_new_valuation_request_task.delay")
    def test_only_saved_request_emits_form_reset_event(self, notify):
        response = self.client.post(reverse("properties:valuation_request_submit"), self.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("HX-Trigger"), "valuation-submitted")
        self.assertEqual(PropertyValuationRequest.objects.count(), 1)
        notify.assert_called_once()

    def test_validation_failure_preserves_form_and_does_not_emit_reset(self):
        response = self.client.post(
            reverse("properties:valuation_request_submit"), {**self.data, "address": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("HX-Trigger", response.headers)
        self.assertEqual(response.context["form"]["name"].value(), self.data["name"])
        self.assertEqual(PropertyValuationRequest.objects.count(), 0)

    def test_rate_limit_does_not_emit_reset_event(self):
        request = RequestFactory().post("/", self.data)
        request.user = AnonymousUser()
        request.limited = True
        view = ValuationRequestCreateView()
        view.setup(request)
        response = view.post(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("HX-Trigger", response.headers)
        self.assertEqual(PropertyValuationRequest.objects.count(), 0)
