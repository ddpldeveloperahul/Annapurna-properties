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

    def test_crm_agent_can_create_lead(self):
        crm_user = User.objects.create_user(username="crm_agent_1", password="crm@123", role=User.Role.CRM)
        from myapp.models import Agent
        agent, _ = Agent.objects.get_or_create(user=crm_user, defaults={"display_name": "CRM Agent 1"})
        
        self.client.force_authenticate(user=crm_user)
        resp = self.client.post(
            "/api/v1/leads/",
            {
                "name": "CRM Buyer",
                "mobile": "9899999999",
                "requirement_type": "Buy",
                "property_type": "Villa",
                "location": "Sarjapur Road",
                "budget_min": 10000000,
                "budget_max": 15000000,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["name"], "CRM Buyer")
        # Assigned to CRM agent by default
        self.assertEqual(resp.data["assigned_to"], agent.id)

    def test_admin_can_activate_and_deactivate_crm_agent(self):
        crm_user = User.objects.create_user(username="crm_agent_2", password="crm@123", role=User.Role.CRM)
        from myapp.models import Agent
        agent, _ = Agent.objects.get_or_create(user=crm_user, defaults={"display_name": "CRM Agent 2"})
        
        # Admin deactivates agent
        admin_user = User.objects.create_superuser(username="superadmin", password="admin123", email="sa@test.com")
        self.client.force_authenticate(user=admin_user)
        
        deact_resp = self.client.post(f"/api/v1/agents/{agent.id}/deactivate/")
        self.assertEqual(deact_resp.status_code, 200)
        agent.refresh_from_db()
        crm_user.refresh_from_db()
        self.assertFalse(agent.is_active)
        self.assertFalse(crm_user.is_active)

        # Deactivated CRM agent cannot create lead
        self.client.force_authenticate(user=crm_user)
        resp = self.client.post(
            "/api/v1/leads/",
            {
                "name": "Blocked Lead",
                "mobile": "9888888888",
                "requirement_type": "Buy",
                "property_type": "Plot",
                "location": "Whitefield",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

        # Admin reactivates agent
        self.client.force_authenticate(user=admin_user)
        act_resp = self.client.post(f"/api/v1/agents/{agent.id}/activate/")
        self.assertEqual(act_resp.status_code, 200)
        agent.refresh_from_db()
        crm_user.refresh_from_db()
        self.assertTrue(agent.is_active)
        self.assertTrue(crm_user.is_active)

        # Reactivated CRM agent can create lead again
        self.client.force_authenticate(user=crm_user)
        resp2 = self.client.post(
            "/api/v1/leads/",
            {
                "name": "Allowed Lead",
                "mobile": "9888888888",
                "requirement_type": "Buy",
                "property_type": "Plot",
                "location": "Whitefield",
            },
            format="json",
        )
        self.assertEqual(resp2.status_code, 201)

    def test_crm_user_cannot_deactivate_other_agents(self):
        crm_user1 = User.objects.create_user(username="crm_1", password="crm@123", role=User.Role.CRM)
        crm_user2 = User.objects.create_user(username="crm_2", password="crm@123", role=User.Role.CRM)
        from myapp.models import Agent
        agent2, _ = Agent.objects.get_or_create(user=crm_user2, defaults={"display_name": "CRM 2"})
        
        self.client.force_authenticate(user=crm_user1)
        resp = self.client.post(f"/api/v1/agents/{agent2.id}/deactivate/")
        self.assertEqual(resp.status_code, 403)

    def test_crm_user_cannot_view_agent_or_account_list(self):
        crm_user = User.objects.create_user(username="crm_viewer", password="crm@123", role=User.Role.CRM)
        admin_user = User.objects.create_superuser(username="admin_viewer", password="admin123", email="av@test.com")
        
        # CRM user cannot view agents list
        self.client.force_authenticate(user=crm_user)
        agents_resp = self.client.get("/api/v1/agents/")
        self.assertEqual(agents_resp.status_code, 403)

        # CRM user cannot view accounts/users list
        accounts_resp = self.client.get("/api/v1/accounts/")
        self.assertEqual(accounts_resp.status_code, 403)

        # Admin CAN view agents list
        self.client.force_authenticate(user=admin_user)
        admin_agents_resp = self.client.get("/api/v1/agents/")
        self.assertEqual(admin_agents_resp.status_code, 200)

        # Admin CAN view accounts list
        admin_acc_resp = self.client.get("/api/v1/accounts/")
        self.assertEqual(admin_acc_resp.status_code, 200)
