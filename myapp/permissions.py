from rest_framework.permissions import BasePermission
from .models import User


class IsAdminRoleOrStaff(BasePermission):
    """
    Grants access only to Admin users (role='admin' or is_staff/is_superuser) who are active.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        return bool(user.is_staff or user.is_superuser or getattr(user, "role", None) == User.Role.ADMIN)


class IsAdminOrCrmAgent(BasePermission):
    """
    Grants read/write access to authenticated Admin and active CRM users.
    Deactivated CRM agents or deactivated users are denied write access.
    """

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False

        # Admin / Superuser have full access
        if user.is_staff or user.is_superuser or getattr(user, "role", None) == User.Role.ADMIN:
            return True

        # CRM users must be active and if they have an agent_profile, it must also be active
        if getattr(user, "role", None) == User.Role.CRM:
            agent = getattr(user, "agent_profile", None)
            if agent is not None and not agent.is_active:
                return False
            return True

        # For safe methods, allow other active authenticated users
        if request.method in self.SAFE_METHODS:
            return True

        return False


class IsStaffOrReadOnly(IsAdminOrCrmAgent):
    """
    Backward-compatible permission class: allows authenticated reads,
    and allows both Admin and active CRM users to write/create leads.
    """
    pass


class IsWebhookCaller(BasePermission):
    """Webhooks are authenticated via a shared-secret header/signature
    checked inside the view itself (see apps.telephony / apps.whatsapp
    webhook validators), not via DRF session/token auth — telephony and
    WhatsApp providers can't hold a Django auth token.
    """

    def has_permission(self, request, view):
        return True
