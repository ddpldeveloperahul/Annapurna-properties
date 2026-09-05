from rest_framework.permissions import BasePermission


class IsStaffOrReadOnly(BasePermission):
    """Any authenticated user can read; only staff/agents can write."""

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def has_permission(self, request, view):
        if request.method in self.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsWebhookCaller(BasePermission):
    """Webhooks are authenticated via a shared-secret header/signature
    checked inside the view itself (see apps.telephony / apps.whatsapp
    webhook validators), not via DRF session/token auth — telephony and
    WhatsApp providers can't hold a Django auth token.
    """

    def has_permission(self, request, view):
        return True
