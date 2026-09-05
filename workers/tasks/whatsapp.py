import logging
from celery import shared_task

logger = logging.getLogger("anpurna_properties")


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
