# pyrefly: ignore [missing-import]
from .models import Lead


def get_lead_by_mobile(mobile: str):
    # pyrefly: ignore [missing-import]
    from .phone import normalize_indian_mobile

    normalized = normalize_indian_mobile(mobile)
    return (
        Lead.objects.filter(mobile=normalized)
        .exclude(status__in=[Lead.Status.CONVERTED, Lead.Status.LOST])
        .order_by("-created_at")
        .first()
    )
