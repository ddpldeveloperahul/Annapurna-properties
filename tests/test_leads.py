from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from myapp.models import Lead
from myapp.services import create_or_update_lead_from_call

User = get_user_model()


class LeadTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass12345", is_staff=True)
        self.client.force_authenticate(user=self.user)

    def test_create_lead_via_api(self):
        resp = self.client.post(
            "/api/v1/leads/",
            {
                "name": "Test Buyer",
                "mobile": "9812345678",
                "requirement_type": "Buy",
                "property_type": "Apartment",
                "location": "Test Nagar",
                "budget_min": 5000000,
                "budget_max": 6000000,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["mobile"], "+919812345678")
        self.assertTrue(resp.data["display_id"].startswith("LD-"))

    def test_duplicate_mobile_updates_not_duplicates(self):
        lead1, created1 = create_or_update_lead_from_call(
            mobile="9812345678", name="A", requirement_type="Buy", property_type="Apartment", location="X",
        )
        lead2, created2 = create_or_update_lead_from_call(
            mobile="+91 98123 45678", name="A", requirement_type="Buy", property_type="Villa", location="Y",
        )
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(lead1.id, lead2.id)
        self.assertEqual(Lead.objects.filter(mobile="+919812345678").count(), 1)

    def test_budget_min_greater_than_max_rejected(self):
        resp = self.client.post(
            "/api/v1/leads/",
            {
                "name": "Bad Budget", "mobile": "9800000001", "requirement_type": "Buy",
                "property_type": "Apartment", "location": "X", "budget_min": 9000000, "budget_max": 5000000,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
