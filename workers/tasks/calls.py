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

    from workers.tasks.leads import create_lead_from_call
    create_lead_from_call.delay(str(call.id))
