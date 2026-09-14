
from unittest.mock import patch, MagicMock
from django.test import TestCase
from myapp.models import WhatsAppMessage, Lead
from myapp.services import send_whatsapp_template
from integrations.whatsapp.client import WhatsAppClient, WhatsAppSendError
import requests


class WhatsAppTemplateTests(TestCase):
    def setUp(self):
        self.lead = Lead.objects.create(
            name="Rahul Kumar",
            mobile="+919876543210",
            requirement_type="Buy",
            property_type="Apartment",
            location="Delhi",
            status=Lead.Status.NEW
        )
        self.template_name = "enquiry_ack_v1"
        self.language = "hi"
        self.parameters = [self.lead.name]

    @patch("integrations.whatsapp.client.requests.post")
    def test_send_template_message(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.1234"}]}
        mock_post.return_value = mock_response

        with self.settings(AI_CALLING_MOCK_PROVIDERS=False):
            # Call our generic service
            message = send_whatsapp_template(
                phone_number=self.lead.mobile,
                template_name=self.template_name,
                language=self.language,
                parameters=self.parameters,
                lead=self.lead
            )

            self.assertEqual(message.status, WhatsAppMessage.Status.SENT)
            self.assertEqual(message.template_name, self.template_name)
            self.assertEqual(message.template_language, self.language)
            self.assertEqual(message.parameters, self.parameters)
            self.assertEqual(message.provider_message_id, "wamid.1234")

            # Check that the Meta API was called with the correct payload structure
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = call_args[1]["json"]

            self.assertEqual(payload["type"], "template")
            self.assertEqual(payload["template"]["name"], self.template_name)
            self.assertEqual(payload["template"]["language"]["code"], self.language)
            
            components = payload["template"]["components"]
            self.assertEqual(len(components), 1)
            self.assertEqual(components[0]["type"], "body")
            self.assertEqual(components[0]["parameters"][0]["text"], "Rahul Kumar")

            # Verify no credentials in logs (though harder to assert directly in tests)
            # Verify access token is in header
            headers = call_args[1]["headers"]
            self.assertTrue(headers["Authorization"].startswith("Bearer "))

    @patch("integrations.whatsapp.client.requests.post")
    def test_failed_meta_api_response(self, mock_post):
        # Simulate a timeout or failure
        mock_post.side_effect = requests.RequestException("Timeout")

        with self.settings(AI_CALLING_MOCK_PROVIDERS=False):
            message = send_whatsapp_template(
                phone_number=self.lead.mobile,
                template_name=self.template_name,
                language=self.language,
                parameters=self.parameters,
                lead=self.lead
            )

            self.assertEqual(message.status, WhatsAppMessage.Status.FAILED)
            self.assertIn("Timeout", message.failure_reason)

    def test_missing_configuration_handled(self):
        # Even if mock is enabled, we can verify it doesn't crash on empty config
        with self.settings(AI_CALLING_MOCK_PROVIDERS=True, WHATSAPP_ACCESS_TOKEN=""):
            message = send_whatsapp_template(
                phone_number=self.lead.mobile,
                template_name=self.template_name,
                language=self.language,
                parameters=self.parameters,
                lead=self.lead
            )
            # Mock mode successfully intercepts
            self.assertTrue(message.status in [WhatsAppMessage.Status.SENT, WhatsAppMessage.Status.FAILED])
