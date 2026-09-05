import logging
from celery import shared_task

logger = logging.getLogger("anpurna_properties")


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

    from workers.tasks.whatsapp import send_followup_whatsapp
    send_followup_whatsapp.delay(str(call.id))
