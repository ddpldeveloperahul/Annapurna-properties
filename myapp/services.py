"""Lead and WhatsApp lifecycle business logic, kept out of views/serializers so both the
REST API and the async call-processing workers (workers/tasks/) can execute through
the same, idempotent path.
"""
import logging
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from integrations.whatsapp.client import WhatsAppClient, WhatsAppSendError
from .models import Agent, Lead, LeadActivity, WhatsAppMessage
from .selectors import get_lead_by_mobile

logger = logging.getLogger("anpurna_properties")


@transaction.atomic
def auto_assign_agent_to_lead(lead: Lead):
    if lead.assigned_to and lead.assigned_to.is_active:
        return lead.assigned_to

    agent = Agent.objects.filter(is_active=True).select_for_update(skip_locked=True).order_by(F('last_assigned_at').asc(nulls_first=True)).first()
    
    if agent:
        assign_agent(lead, agent)
        agent.last_assigned_at = timezone.now()
        agent.save(update_fields=["last_assigned_at", "updated_at"])
        return agent
    return None


@transaction.atomic
def create_or_update_lead_from_call(*, mobile, name, requirement_type, property_type,
                                      budget_min=None, budget_max=None, location="",
                                      timeline="", interest_level="", source=Lead.Source.AI_CALL):
    existing = get_lead_by_mobile(mobile)

    if existing:
        existing.name = name or existing.name
        existing.requirement_type = requirement_type or existing.requirement_type
        existing.property_type = property_type or existing.property_type
        existing.budget_min = budget_min if budget_min is not None else existing.budget_min
        existing.budget_max = budget_max if budget_max is not None else existing.budget_max
        existing.location = location or existing.location
        existing.timeline = timeline or existing.timeline
        existing.interest_level = interest_level or existing.interest_level
        existing.last_activity_at = timezone.now()
        existing.save()
        LeadActivity.objects.create(
            lead=existing,
            activity_type=LeadActivity.ActivityType.CALL_LOGGED,
            description="New AI call logged against existing lead",
        )
        logger.info("Updated existing lead %s from call", existing.display_id)
        auto_assign_agent_to_lead(existing)
        return existing, False

    lead = Lead.objects.create(
        name=name,
        mobile=mobile,
        source=source,
        status=Lead.Status.NEW,
        requirement_type=requirement_type,
        property_type=property_type,
        budget_min=budget_min,
        budget_max=budget_max,
        location=location,
        timeline=timeline,
        interest_level=interest_level,
        last_activity_at=timezone.now(),
    )
    LeadActivity.objects.create(
        lead=lead,
        activity_type=LeadActivity.ActivityType.CALL_LOGGED,
        description="Lead created from AI call",
    )
    logger.info("Created new lead %s from call", lead.display_id)
    auto_assign_agent_to_lead(lead)
    return lead, True


def change_status(lead: Lead, new_status: str, actor=None):
    old_status = lead.status
    lead.status = new_status
    lead.last_activity_at = timezone.now()
    lead.save(update_fields=["status", "last_activity_at", "updated_at"])
    LeadActivity.objects.create(
        lead=lead,
        activity_type=LeadActivity.ActivityType.STATUS_CHANGE,
        description=f"Status changed from {old_status} to {new_status}",
        actor=actor,
    )
    return lead


def assign_agent(lead: Lead, agent, actor=None):
    lead.assigned_to = agent
    lead.last_activity_at = timezone.now()
    lead.save(update_fields=["assigned_to", "last_activity_at", "updated_at"])
    LeadActivity.objects.create(
        lead=lead,
        activity_type=LeadActivity.ActivityType.ASSIGNMENT,
        description=f"Assigned to {agent.display_name if agent else 'Unassigned'}",
        actor=actor,
    )
    return lead


# --- WhatsApp Services ----------------------------------------------------
def send_whatsapp_template(phone_number: str, template_name: str, language: str, parameters: list, lead=None, call=None):
    from myapp.phone import normalize_indian_mobile
    normalized_phone = normalize_indian_mobile(phone_number)

    # Render a preview body for storage
    body_preview = f"Template: {template_name}\nLanguage: {language}\nParams: {parameters}"

    message = WhatsAppMessage.objects.create(
        lead=lead,
        call=call,
        to_number=normalized_phone,
        template_name=template_name,
        template_language=language,
        parameters=parameters,
        body=body_preview,
        status=WhatsAppMessage.Status.QUEUED,
    )
    return _dispatch_whatsapp(message)


def send_lead_acknowledgement(lead, call=None):
    existing = WhatsAppMessage.objects.filter(lead=lead, call=call, template_name=settings.WHATSAPP_TEMPLATE_NAME).first()
    if existing:
        return existing

    # Assuming template {{1}} is customer name
    parameters = [lead.name or "Customer"]
    return send_whatsapp_template(
        phone_number=lead.mobile,
        template_name=settings.WHATSAPP_TEMPLATE_NAME,
        language=settings.WHATSAPP_TEMPLATE_LANG,
        parameters=parameters,
        lead=lead,
        call=call
    )


def resend_whatsapp(message: WhatsAppMessage):
    message.failure_reason = ""
    message.status = WhatsAppMessage.Status.QUEUED
    message.save(update_fields=["failure_reason", "status", "updated_at"])
    return _dispatch_whatsapp(message)


def _dispatch_whatsapp(message: WhatsAppMessage):
    client = WhatsAppClient()
    try:
        result = client.send_template(
            to_number=message.to_number,
            template_name=message.template_name,
            language=message.template_language,
            body_preview=message.body,
            parameters=message.parameters,
        )
        message.provider_message_id = result["message_id"]
        message.status = WhatsAppMessage.Status.SENT
        message.sent_at = timezone.now()
    except WhatsAppSendError as exc:
        message.status = WhatsAppMessage.Status.FAILED
        message.failure_reason = str(exc)
        logger.warning("WhatsApp send failed for %s: %s", message.display_id, exc)
    message.save()
    return message


def _render_whatsapp_template(lead):
    budget = ""
    if lead.budget_min and lead.budget_max:
        budget = f", budget ₹{int(lead.budget_min):,} – ₹{int(lead.budget_max):,}"
    return (
        f"Namaste {lead.name}, thank you for your enquiry with us. "
        f"We've noted your requirement: {lead.requirement_type} {lead.property_type} "
        f"in {lead.location}{budget}. Our team will contact you shortly."
    )


def _template_parameters(lead):
    budget = ""
    if lead.budget_min and lead.budget_max:
        budget = f"₹{int(lead.budget_min):,} - ₹{int(lead.budget_max):,}"
    return [lead.name or "Customer", lead.requirement_type or "", lead.property_type or "", lead.location or "", budget]
