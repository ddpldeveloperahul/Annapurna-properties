from django.test import TestCase
from django.utils import timezone
from myapp.models import Agent, Lead, User
from myapp.services import auto_assign_agent_to_lead

class AgentAssignmentTests(TestCase):
    def setUp(self):
        # Create users for agents
        self.user1 = User.objects.create(username="user1")
        self.user2 = User.objects.create(username="user2")
        self.user3 = User.objects.create(username="user3")
        
        # Create agents
        self.agent1 = Agent.objects.create(user=self.user1, display_name="Agent 1", is_active=True)
        self.agent2 = Agent.objects.create(user=self.user2, display_name="Agent 2", is_active=True)
        self.agent3 = Agent.objects.create(user=self.user3, display_name="Agent 3", is_active=True)

    def _create_lead(self, mobile, assigned_to=None):
        return Lead.objects.create(
            name="Test Lead",
            mobile=mobile,
            requirement_type=Lead.RequirementType.BUY,
            property_type="Apartment",
            location="Test Location",
            assigned_to=assigned_to
        )

    def test_existing_lead_same_assigned_agent(self):
        lead = self._create_lead("+910000000001", assigned_to=self.agent1)
        assigned_agent = auto_assign_agent_to_lead(lead)
        self.assertEqual(assigned_agent, self.agent1)

    def test_existing_assigned_agent_unavailable_fallback(self):
        # Agent 1 is assigned but inactive
        self.agent1.is_active = False
        self.agent1.save()
        
        lead = self._create_lead("+910000000002", assigned_to=self.agent1)
        assigned_agent = auto_assign_agent_to_lead(lead)
        self.assertNotEqual(assigned_agent, self.agent1)
        self.assertIn(assigned_agent, [self.agent2, self.agent3])

    def test_inactive_agent_never_selected(self):
        self.agent2.is_active = False
        self.agent2.save()
        self.agent3.is_active = False
        self.agent3.save()
        
        lead = self._create_lead("+910000000003")
        assigned_agent = auto_assign_agent_to_lead(lead)
        self.assertEqual(assigned_agent, self.agent1)

    def test_all_agents_unavailable(self):
        self.agent1.is_active = False
        self.agent1.save()
        self.agent2.is_active = False
        self.agent2.save()
        self.agent3.is_active = False
        self.agent3.save()
        
        lead = self._create_lead("+910000000004")
        assigned_agent = auto_assign_agent_to_lead(lead)
        self.assertIsNone(assigned_agent)
        
        # Verify lead is still unassigned
        lead.refresh_from_db()
        self.assertIsNone(lead.assigned_to)

    def test_fair_round_robin_three_agents(self):
        # Assign to 6 leads to check round-robin
        agents_assigned = []
        for i in range(6):
            lead = self._create_lead(f"+91000000001{i}")
            agent = auto_assign_agent_to_lead(lead)
            agents_assigned.append(agent)
            
        # Should be distributed equally
        self.assertEqual(agents_assigned.count(self.agent1), 2)
        self.assertEqual(agents_assigned.count(self.agent2), 2)
        self.assertEqual(agents_assigned.count(self.agent3), 2)

    def test_one_agent_all_new_leads(self):
        self.agent2.is_active = False
        self.agent2.save()
        self.agent3.is_active = False
        self.agent3.save()
        
        for i in range(5):
            lead = self._create_lead(f"+91000000002{i}")
            agent = auto_assign_agent_to_lead(lead)
            self.assertEqual(agent, self.agent1)

    def test_five_agents_dynamic_assignment(self):
        # Create 2 more agents
        user4 = User.objects.create(username="user4")
        user5 = User.objects.create(username="user5")
        agent4 = Agent.objects.create(user=user4, display_name="Agent 4", is_active=True)
        agent5 = Agent.objects.create(user=user5, display_name="Agent 5", is_active=True)
        
        agents_assigned = []
        for i in range(10):
            lead = self._create_lead(f"+91000000003{i}")
            agent = auto_assign_agent_to_lead(lead)
            agents_assigned.append(agent)
            
        # Every agent should get exactly 2 leads
        self.assertEqual(agents_assigned.count(self.agent1), 2)
        self.assertEqual(agents_assigned.count(self.agent2), 2)
        self.assertEqual(agents_assigned.count(self.agent3), 2)
        self.assertEqual(agents_assigned.count(agent4), 2)
        self.assertEqual(agents_assigned.count(agent5), 2)

