import logging

logger = logging.getLogger("anpurna_properties")

WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


class AuditLogMiddleware:
    """Lightweight request-level audit trail. Writes a row for every
    mutating API/webhook call so support staff can trace a lead or call
    back to the request that created or changed it.

    Kept deliberately dependency-free (no DB write on GETs) so it never
    becomes a bottleneck on the hot dashboard/list endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method in WRITE_METHODS and request.path.startswith("/api/"):
            self._record(request, response)
        return response

    def _record(self, request, response):
        try:
            from .models import AuditLog

            actor = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            AuditLog.objects.create(
                actor=actor,
                actor_label=getattr(actor, "email", None) or "anonymous/webhook",
                action=request.method,
                object_type="http_request",
                object_id="",
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                metadata={},
            )
        except Exception:  # pragma: no cover - audit logging must never break the request
            logger.exception("Failed to write audit log for %s %s", request.method, request.path)
