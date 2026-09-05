"""Seeds the database with the same demo dataset the frontend ships with
(src/data/dummyData.js) so a backend + frontend demo shows consistent
leads, calls, transcripts, summaries, follow-ups and WhatsApp messages.

Usage:
    python manage.py seed_demo_data [--reset]
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from myapp.models import Agent, Call, CallSummary, CallTranscript, Followup, Lead, WhatsAppMessage

User = get_user_model()


def days_ago(n, hour=10, minute=0):
    d = timezone.now() - timedelta(days=n)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)


def days_ahead(n, hour=10, minute=0):
    d = timezone.now() + timedelta(days=n)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)


AGENTS = [
    {"username": "priya.menon", "first_name": "Priya", "last_name": "Menon", "display_name": "Priya Menon"},
    {"username": "rohit.sharma", "first_name": "Rohit", "last_name": "Sharma", "display_name": "Rohit Sharma"},
    {"username": "ayesha.khan", "first_name": "Ayesha", "last_name": "Khan", "display_name": "Ayesha Khan"},
]

LEADS = [
    dict(display_id="LD-1042", name="Anjali Verma", mobile="+919811123456", status=Lead.Status.QUALIFIED,
         requirement_type="Buy", property_type="Apartment", budget_min=8500000, budget_max=11000000,
         location="Sector 62, Noida", timeline="1-3 months", interest_level="High", agent_idx=0,
         created=days_ago(0, 9, 15)),
    dict(display_id="LD-1041", name="Karan Malhotra", mobile="+919822265432", status=Lead.Status.NEEDS_HUMAN,
         requirement_type="Rent", property_type="Villa", budget_min=60000, budget_max=90000,
         location="Whitefield, Bangalore", timeline="Immediate", interest_level="High", agent_idx=1,
         created=days_ago(0, 8, 5)),
    dict(display_id="LD-1040", name="Meera Iyer", mobile="+919833311223", status=Lead.Status.FOLLOWUP_SCHEDULED,
         requirement_type="Buy", property_type="Plot", budget_min=3000000, budget_max=4200000,
         location="Sarjapur Road, Bangalore", timeline="3-6 months", interest_level="Medium", agent_idx=2,
         created=days_ago(1, 17, 40)),
    dict(display_id="LD-1039", name="Deepak Nair", mobile="+919844455667", status=Lead.Status.CONTACTED,
         requirement_type="Sell", property_type="Independent House", budget_min=9000000, budget_max=9500000,
         location="Kothrud, Pune", timeline="Not urgent", interest_level="Medium", agent_idx=0,
         created=days_ago(1, 12, 10)),
    dict(display_id="LD-1038", name="Simran Kaur", mobile="+919855599887", status=Lead.Status.NEW,
         requirement_type="Buy", property_type="Apartment", budget_min=5500000, budget_max=7000000,
         location="Zirakpur, Chandigarh", timeline="6+ months", interest_level="Low", agent_idx=None,
         created=days_ago(2, 9, 0)),
    dict(display_id="LD-1037", name="Vikram Rao", mobile="+919866644332", status=Lead.Status.CONVERTED,
         requirement_type="Buy", property_type="Villa", budget_min=15000000, budget_max=18000000,
         location="ECR, Chennai", timeline="Immediate", interest_level="High", agent_idx=1,
         created=days_ago(4, 14, 20)),
    dict(display_id="LD-1036", name="Fatima Sheikh", mobile="+919877722110", status=Lead.Status.LOST,
         requirement_type="Rent", property_type="Apartment", budget_min=25000, budget_max=35000,
         location="Andheri West, Mumbai", timeline="Immediate", interest_level="Low", agent_idx=2,
         created=days_ago(5, 16, 0)),
    dict(display_id="LD-1035", name="Arjun Reddy", mobile="+919888877665", status=Lead.Status.QUALIFIED,
         requirement_type="Buy", property_type="Apartment", budget_min=6000000, budget_max=7500000,
         location="Gachibowli, Hyderabad", timeline="1-3 months", interest_level="High", agent_idx=0,
         created=days_ago(2, 18, 30)),
]

CALLS = [
    dict(display_id="CL-5231", lead_id="LD-1042", from_number="+919811123456", status=Call.Status.COMPLETED,
         duration=214, started=days_ago(0, 9, 15), has_recording=True,
         transcript=[
             {"speaker": "AI", "text": "Namaste! Aap Basera Realty se baat kar rahe hain. Kya aap ghar khareedna, bechna, ya kiraye par lena chahte hain?"},
             {"speaker": "Customer", "text": "Main ek 2BHK apartment khareedna chahti hoon, Noida Sector 62 ke aas-paas."},
             {"speaker": "AI", "text": "Aapka budget range kya hai is property ke liye?"},
             {"speaker": "Customer", "text": "Kareeb 85 lakh se 1.1 crore ke beech."},
             {"speaker": "AI", "text": "Dhanyavaad Anjali ji, hamari team jald hi aapse sampark karegi."},
         ],
         summary=dict(requirement="2BHK apartment purchase near Sector 62, Noida", budget_text="₹85L – ₹1.1Cr",
                      location="Sector 62, Noida", interest_level="High",
                      key_points=["First-time buyer, wants possession-ready unit", "Open to site visit this weekend"],
                      suggested_action="Schedule site visit for Sector 62 listings", follow_up=days_ahead(1, 11, 0))),
    dict(display_id="CL-5230", lead_id="LD-1041", from_number="+919822265432", status=Call.Status.COMPLETED,
         duration=168, started=days_ago(0, 8, 5), has_recording=True,
         transcript=[
             {"speaker": "AI", "text": "Hello, Basera Realty se baat kar rahi hoon. Kya main aapki madad kar sakti hoon?"},
             {"speaker": "Customer", "text": "Haan, mujhe Whitefield mein ek villa chahiye rent pe, urgent hai."},
             {"speaker": "Customer", "text": "Mujhe kisi insaan se baat karni hai."},
             {"speaker": "AI", "text": "Bilkul, main aapko humare team member se connect karwa deti hoon."},
         ],
         summary=dict(requirement="Villa rental in Whitefield, Bangalore", budget_text="₹60,000 – ₹90,000/mo",
                      location="Whitefield, Bangalore", interest_level="High",
                      key_points=["Customer explicitly requested a human agent", "Urgent — needs to move within the week"],
                      suggested_action="Human agent callback today", follow_up=days_ahead(0, 15, 0))),
    dict(display_id="CL-5229", lead_id="LD-1040", from_number="+919833311223", status=Call.Status.COMPLETED,
         duration=191, started=days_ago(1, 17, 40), has_recording=True,
         transcript=[
             {"speaker": "AI", "text": "Namaste, aap property khareedna chahte hain ya bechna?"},
             {"speaker": "Customer", "text": "Ek residential plot khareedna hai, Sarjapur Road ke aas paas."},
             {"speaker": "Customer", "text": "Budget 30 se 42 lakh tak."},
         ],
         summary=dict(requirement="Residential plot purchase near Sarjapur Road", budget_text="₹30L – ₹42L",
                      location="Sarjapur Road, Bangalore", interest_level="Medium",
                      key_points=["Not in a hurry", "Comparing 2-3 nearby projects"],
                      suggested_action="Send plot listings shortlist by WhatsApp", follow_up=days_ahead(2, 12, 30))),
    dict(display_id="CL-5228", lead_id="LD-1039", from_number="+919844455667", status=Call.Status.COMPLETED,
         duration=143, started=days_ago(1, 12, 10), has_recording=False,
         transcript=[
             {"speaker": "AI", "text": "Namaste, kya aap property bechna chahte hain?"},
             {"speaker": "Customer", "text": "Haan, Kothrud Pune mein mera independent house hai, bechna hai."},
         ],
         summary=dict(requirement="Independent house sale in Kothrud, Pune", budget_text="₹90L – ₹95L (asking)",
                      location="Kothrud, Pune", interest_level="Medium",
                      key_points=["Call disconnected before timeline was captured"],
                      suggested_action="Callback to confirm timeline and documents", follow_up=days_ahead(3, 10, 0))),
    dict(display_id="CL-5227", lead_id="LD-1038", from_number="+919855599887", status=Call.Status.COMPLETED,
         duration=96, started=days_ago(2, 9, 0), has_recording=True,
         transcript=[
             {"speaker": "AI", "text": "Namaste, property khareedne ka plan hai kya?"},
             {"speaker": "Customer", "text": "Haan bas dekh rahi hoon, abhi kuch decide nahi kiya."},
         ],
         summary=dict(requirement="Early-stage apartment search near Zirakpur", budget_text="₹55L – ₹70L",
                      location="Zirakpur, Chandigarh", interest_level="Low",
                      key_points=["Browsing stage, not ready to commit"],
                      suggested_action="Add to nurture WhatsApp sequence", follow_up=None)),
    dict(display_id="CL-5226", lead_id="LD-1037", from_number="+919866644332", status=Call.Status.COMPLETED,
         duration=260, started=days_ago(4, 14, 20), has_recording=True,
         transcript=[
             {"speaker": "AI", "text": "Namaste, aap kya dhundh rahe hain?"},
             {"speaker": "Customer", "text": "ECR Chennai mein ek villa chahiye, ready to move."},
         ],
         summary=dict(requirement="Villa purchase on ECR, Chennai", budget_text="₹1.5Cr – ₹1.8Cr",
                      location="ECR, Chennai", interest_level="High",
                      key_points=["Deal closed after 2 site visits"],
                      suggested_action="Converted — move to post-sale handover", follow_up=None)),
    dict(display_id="CL-5225", lead_id="LD-1036", from_number="+919877722110", status=Call.Status.FAILED,
         duration=0, started=days_ago(5, 16, 0), has_recording=False, transcript=[], summary=None),
    dict(display_id="CL-5224", lead_id="LD-1035", from_number="+919888877665", status=Call.Status.COMPLETED,
         duration=205, started=days_ago(2, 18, 30), has_recording=True,
         transcript=[
             {"speaker": "AI", "text": "Namaste, aap property khareedna chahte hain?"},
             {"speaker": "Customer", "text": "Haan, Gachibowli mein 3BHK apartment chahiye, budget 60 se 75 lakh."},
         ],
         summary=dict(requirement="3BHK apartment purchase in Gachibowli, Hyderabad", budget_text="₹60L – ₹75L",
                      location="Gachibowli, Hyderabad", interest_level="High",
                      key_points=["IT professional, wants proximity to tech parks"],
                      suggested_action="Share shortlisted listings before site visit", follow_up=days_ahead(1, 16, 0))),
]


class Command(BaseCommand):
    help = "Seed the database with demo leads, calls, transcripts, summaries, follow-ups and WhatsApp messages."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo data first.")

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Clearing existing data...")
            WhatsAppMessage.objects.all().delete()
            Followup.objects.all().delete()
            CallSummary.objects.all().delete()
            CallTranscript.objects.all().delete()
            Call.objects.all().delete()
            Lead.objects.all().delete()
            Agent.objects.all().delete()

        agents = []
        for a in AGENTS:
            user, _ = User.objects.get_or_create(
                username=a["username"],
                defaults={"first_name": a["first_name"], "last_name": a["last_name"], "role": "CRM"},
            )
            if not user.has_usable_password():
                user.set_password("demo-pass-123")
                user.save()
            agent, _ = Agent.objects.get_or_create(user=user, defaults={"display_name": a["display_name"]})
            agents.append(agent)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(agents)} agents"))

        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser("admin", "admin@basera-realty.example", "admin-pass-123")
            self.stdout.write(self.style.SUCCESS("Created superuser 'admin' / 'admin-pass-123'"))

        leads_by_display_id = {}
        for l in LEADS:
            agent = agents[l["agent_idx"]] if l["agent_idx"] is not None else None
            lead, _ = Lead.objects.update_or_create(
                display_id=l["display_id"],
                defaults=dict(
                    name=l["name"], mobile=l["mobile"], status=l["status"], source=Lead.Source.AI_CALL,
                    requirement_type=l["requirement_type"], property_type=l["property_type"],
                    budget_min=l["budget_min"], budget_max=l["budget_max"], location=l["location"],
                    timeline=l["timeline"], interest_level=l["interest_level"], assigned_to=agent,
                    last_activity_at=l["created"],
                ),
            )
            Lead.objects.filter(pk=lead.pk).update(created_at=l["created"])
            leads_by_display_id[l["display_id"]] = lead
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(leads_by_display_id)} leads"))

        whatsapp_count = 0
        for c in CALLS:
            lead = leads_by_display_id.get(c["lead_id"])
            call, _ = Call.objects.update_or_create(
                display_id=c["display_id"],
                defaults=dict(
                    lead=lead, provider="exotel", provider_call_sid=f"mock-{c['display_id'].lower()}",
                    direction=Call.Direction.INBOUND, from_number=c["from_number"], status=c["status"],
                    started_at=c["started"], ended_at=c["started"] + timedelta(seconds=c["duration"]),
                    duration_sec=c["duration"],
                    recording_url=f"https://mock-exotel-recordings.example.com/{c['display_id']}.mp3" if c["has_recording"] else "",
                ),
            )
            if c["transcript"]:
                CallTranscript.objects.update_or_create(
                    call=call,
                    defaults=dict(
                        turns=c["transcript"],
                        full_text="\n".join(f"{t['speaker']}: {t['text']}" for t in c["transcript"]),
                    ),
                )
            if c["summary"]:
                s = c["summary"]
                CallSummary.objects.update_or_create(
                    call=call,
                    defaults=dict(
                        requirement=s["requirement"], budget_text=s["budget_text"], location=s["location"],
                        interest_level=s["interest_level"], key_points=s["key_points"],
                        suggested_action=s["suggested_action"], follow_up_date=s["follow_up"],
                    ),
                )
                if lead and s["follow_up"]:
                    Followup.objects.get_or_create(
                        lead=lead, followup_type=Followup.FollowupType.CALL, status=Followup.Status.PENDING,
                        defaults=dict(note=s["suggested_action"], due_at=s["follow_up"], assigned_to=lead.assigned_to),
                    )
                if lead:
                    body = (
                        f"Namaste {lead.name}, Basera Realty mein enquiry ke liye dhanyavaad. "
                        f"Humein pata chala aap {lead.location} mein {lead.property_type.lower()} dhundh rahe hain. "
                        f"Hamari team jald hi aapse sampark karegi."
                    )
                    wa_status = WhatsAppMessage.Status.READ if c["status"] == Call.Status.COMPLETED else WhatsAppMessage.Status.FAILED
                    WhatsAppMessage.objects.get_or_create(
                        lead=lead, call=call, template_name="enquiry_ack_v1",
                        defaults=dict(
                            to_number=lead.mobile, body=body, status=wa_status,
                            sent_at=call.ended_at, provider_message_id=f"wamock.{call.display_id.lower()}",
                            failure_reason="" if wa_status != WhatsAppMessage.Status.FAILED else "Recipient number not on WhatsApp",
                        ),
                    )
                    whatsapp_count += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(CALLS)} calls and {whatsapp_count} WhatsApp messages"))

        self.stdout.write(self.style.SUCCESS("Demo data seed complete."))
