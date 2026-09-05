"""Celery async tasks for myapp.

Contains all 4 worker task pipelines (calls, leads, summaries, whatsapp) directly:
1. start_ai_conversation & finalize_completed_call (calls)
2. fetch_and_store_transcript (calls)
3. create_lead_from_call (leads)
4. generate_call_summary (summaries)
5. send_followup_whatsapp (whatsapp)
"""
import logging
from celery import shared_task

logger = logging.getLogger("anpurna_properties")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=120, retry_jitter=True, max_retries=5)
def start_ai_conversation(self, call_id: str):
    from django.conf import settings
    from myapp.models import AISession, Call

    try:
        call = Call.objects.get(id=call_id)
    except Call.DoesNotExist:
        logger.warning("start_ai_conversation: call %s not found", call_id)
        return

    AISession.objects.get_or_create(call=call, defaults={"stage": AISession.Stage.GREETING})

    if settings.AI_CALLING_MOCK_PROVIDERS:
        call.status = Call.Status.COMPLETED
        call.duration_sec = 180
        call.save(update_fields=["status", "duration_sec", "updated_at"])
        finalize_completed_call.delay(str(call.id))


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=120, retry_jitter=True, max_retries=5)
def finalize_completed_call(self, call_id: str):
    from myapp.models import Call, CallEvent

    try:
        call = Call.objects.get(id=call_id)
    except Call.DoesNotExist:
        logger.warning("finalize_completed_call: call %s not found", call_id)
        return

    CallEvent.objects.create(call=call, event_type="pipeline_started", payload={})
    fetch_and_store_transcript.delay(str(call.id))


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=120, retry_jitter=True, max_retries=5)
def fetch_and_store_transcript(self, call_id: str):
    from myapp.models import Call, CallTranscript
    from integrations.elevenlabs.client import ElevenLabsClient

    call = Call.objects.get(id=call_id)
    if hasattr(call, "transcript"):
        logger.info("Transcript already stored for %s, skipping re-fetch", call.display_id)
    else:
        from django.conf import settings
        conversation_id = call.voice_conversation_id
        if not conversation_id and settings.AI_CALLING_MOCK_PROVIDERS:
            conversation_id = call.provider_call_sid or str(call.id)
        if not conversation_id:
            raise RuntimeError(f"No ElevenLabs conversation id stored for {call.display_id}")
        turns = ElevenLabsClient().fetch_conversation_transcript(conversation_id)
        CallTranscript.objects.create(call=call, turns=turns, full_text="\n".join(f"{t['speaker']}: {t['text']}" for t in turns))

        from integrations.exotel.client import ExotelClient
        call.recording_url = call.recording_url or ExotelClient().fetch_recording_url(call.provider_call_sid or str(call.id))
        call.save(update_fields=["recording_url", "updated_at"])

    create_lead_from_call.delay(str(call.id))


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
    generate_call_summary.delay(str(call.id))


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=120, retry_jitter=True, max_retries=5)
def generate_call_summary(self, call_id: str):
    from django.utils import timezone
    from myapp.models import Call, CallSummary, Followup
    from myapp.llm import LLMClient

    call = Call.objects.select_related("transcript", "lead").get(id=call_id)
    summary_data = LLMClient().generate_call_summary(call.transcript.turns, lead=call.lead)

    CallSummary.objects.update_or_create(
        call=call,
        defaults={
            **summary_data,
            "follow_up_date": timezone.now() + timezone.timedelta(days=1),
        },
    )

    if call.lead:
        Followup.objects.get_or_create(
            lead=call.lead,
            followup_type=Followup.FollowupType.CALL,
            status=Followup.Status.PENDING,
            defaults={
                "note": summary_data["suggested_action"],
                "due_at": timezone.now() + timezone.timedelta(days=1),
                "assigned_to": call.lead.assigned_to,
            },
        )

    logger.info("Summary generated for call %s", call.display_id)
    send_followup_whatsapp.delay(str(call.id))


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=120, retry_jitter=True, max_retries=5)
def send_followup_whatsapp(self, call_id: str):
    from myapp.models import Call
    from myapp import services as myapp_services

    call = Call.objects.select_related("lead").get(id=call_id)
    if not call.lead:
        logger.warning("No lead linked to call %s, skipping WhatsApp send", call.display_id)
        return

    message = myapp_services.send_lead_acknowledgement(call.lead, call=call)
    logger.info("WhatsApp %s for call %s: %s", message.display_id, call.display_id, message.status)
