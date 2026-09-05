import json
from django.test import override_settings
from rest_framework.test import APITestCase
from myapp.models import Call, WhatsAppMessage


class WebhookTestCase(APITestCase):
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_incoming_call_then_completion_runs_full_pipeline(self):
        resp = self.client.post(
            "/api/v1/telephony/webhooks/incoming-call/",
            data=json.dumps({"call_sid": "sid-xyz", "from_number": "+919000000001"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

        resp2 = self.client.post(
            "/api/v1/telephony/webhooks/call-status/",
            data=json.dumps({"call_sid": "sid-xyz", "status": "Completed", "duration_sec": 120}),
            content_type="application/json",
        )
        self.assertEqual(resp2.status_code, 200)

        call = Call.objects.get(provider_call_sid="sid-xyz")
        self.assertEqual(call.status, "Completed")
        self.assertIsNotNone(call.lead)
        self.assertTrue(hasattr(call, "transcript"))
        self.assertTrue(hasattr(call, "summary"))
        self.assertTrue(WhatsAppMessage.objects.filter(call=call).exists())

    def test_webhook_retries_are_idempotent(self):
        payload = json.dumps({"call_sid": "sid-retry", "from_number": "+919000000002"})
        for _ in range(3):
            self.client.post("/api/v1/telephony/webhooks/incoming-call/", data=payload, content_type="application/json")
        self.assertEqual(Call.objects.filter(provider_call_sid="sid-retry").count(), 1)

    def test_failed_call_is_still_logged(self):
        self.client.post(
            "/api/v1/telephony/webhooks/incoming-call/",
            data=json.dumps({"call_sid": "sid-failed", "from_number": "+919000000003"}),
            content_type="application/json",
        )
        resp = self.client.post(
            "/api/v1/telephony/webhooks/call-status/",
            data=json.dumps({"call_sid": "sid-failed", "status": "Failed"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        call = Call.objects.get(provider_call_sid="sid-failed")
        self.assertEqual(call.status, "Failed")
