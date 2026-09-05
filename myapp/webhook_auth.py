import hashlib
import hmac

from django.conf import settings


def verify_exotel_signature(request) -> bool:
    """Validate the shared-secret signature Exotel is configured to send.

    In mock mode (default for this POC) we skip verification so the
    webhook can be exercised with curl/Postman without provisioning a real
    Exotel account. In live mode, requests without a valid signature are
    rejected with 401 before anything is written to the database.
    """
    if settings.AI_CALLING_MOCK_PROVIDERS:
        return True
    secret = settings.EXOTEL_WEBHOOK_SECRET
    if not secret:
        return False
    signature = request.headers.get("X-Exotel-Signature", "")
    expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
