"""AI qualification state machine.

Mirrors docs/ai/conversation-flow.md exactly:

    START -> GREETING -> INTENT -> PROPERTY_TYPE -> BUDGET -> LOCATION
    -> TIMELINE -> CONFIRMATION -> COMPLETE

Rules encoded here (from the dev plan section 8 and SOW 3.2):
  - Ask only for missing qualification information.
  - Re-ask an unclear answer once; on a second miss, route to human handoff.
  - Immediate human handoff if the caller explicitly asks for a person.
  - Never invent property inventory, pricing, or availability.
"""
from django.conf import settings

from .models import AISession

ORDER = [
    AISession.Stage.START,
    AISession.Stage.GREETING,
    AISession.Stage.INTENT,
    AISession.Stage.PROPERTY_TYPE,
    AISession.Stage.BUDGET,
    AISession.Stage.LOCATION,
    AISession.Stage.TIMELINE,
    AISession.Stage.CONFIRMATION,
    AISession.Stage.COMPLETE,
]

FIELD_FOR_STAGE = {
    AISession.Stage.INTENT: "requirement_type",
    AISession.Stage.PROPERTY_TYPE: "property_type",
    AISession.Stage.BUDGET: "budget",
    AISession.Stage.LOCATION: "location",
    AISession.Stage.TIMELINE: "timeline",
}


def next_stage(current: str) -> str:
    idx = ORDER.index(current)
    return ORDER[min(idx + 1, len(ORDER) - 1)]


def advance(session: AISession, extracted_value=None, customer_requested_human=False, was_unclear=False):
    """Apply one turn's outcome to the session and return the new stage.

    This is intentionally pure w.r.t. side effects other than mutating and
    saving `session`, so it's unit-testable without a real voice provider.
    """
    if customer_requested_human:
        session.stage = AISession.Stage.HUMAN_HANDOFF
        session.ended_reason = "customer_requested_human"
        session.save(update_fields=["stage", "ended_reason", "updated_at"])
        return session.stage

    field = FIELD_FOR_STAGE.get(session.stage)

    if was_unclear and field:
        session.clarify_attempts += 1
        if session.clarify_attempts > settings.AI_QUALIFICATION_MAX_CLARIFY_ATTEMPTS:
            session.stage = AISession.Stage.HUMAN_HANDOFF
            session.ended_reason = "repeated_misunderstanding"
        session.save(update_fields=["clarify_attempts", "stage", "ended_reason", "updated_at"])
        return session.stage

    if field and extracted_value is not None:
        session.extracted_fields[field] = extracted_value
        session.clarify_attempts = 0

    session.stage = next_stage(session.stage)
    session.save(update_fields=["stage", "clarify_attempts", "extracted_fields", "updated_at"])
    return session.stage
