import logging
from celery import shared_task

logger = logging.getLogger("anpurna_properties")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=120, retry_jitter=True, max_retries=5)
def create_lead_from_call(self, call_id: str):
    from myapp.models import Call, CallEvent, Lead
    from myapp.services import create_or_update_lead_from_call
    from myapp.llm import LLMClient

    call = Call.objects.select_related("transcript", "lead").get(id=call_id)
    fields = LLMClient().extract_qualification_fields(call.transcript.turns)
    lead, created = create_or_update_lead_from_call(
        mobile=call.from_number,
        name=fields.get("customer_name") or (call.lead.name if call.lead else "Unknown Caller"),
        requirement_type=fields["requirement_type"],
        property_type=fields["property_type"],
        budget_min=fields.get("budget_min"),
        budget_max=fields.get("budget_max"),
        location=fields.get("location", "") or (call.lead.location if call.lead else ""),
        timeline=fields.get("timeline", "") or (call.lead.timeline if call.lead else ""),
        interest_level=fields.get("interest_level") or (call.lead.interest_level if call.lead else "Medium"),
    )
    if fields.get("needs_human_followup"):
        lead.status = Lead.Status.NEEDS_HUMAN
        lead.save(update_fields=["status", "updated_at"])
        CallEvent.objects.create(call=call, event_type="human_followup_required", payload={"reason": fields.get("human_followup_reason", "")})
    
    if call.lead_id != lead.id:
        call.lead = lead
        call.save(update_fields=["lead", "updated_at"])
    
    logger.info("Lead %s %s for call %s", lead.display_id, "created" if created else "updated", call.display_id)
    
    from workers.tasks.summaries import generate_call_summary
    generate_call_summary.delay(str(call.id))
