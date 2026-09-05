import logging

from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("anpurna_properties")


def api_exception_handler(exc, context):
    """Wrap DRF's default handler so every error response has a consistent
    {"error": {"code": ..., "message": ..., "detail": ...}} shape and gets
    logged with the view/request context for debugging.
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        view = context.get("view")
        logger.warning(
            "API error in %s: %s",
            getattr(view, "__class__", type(view)).__name__ if view else "unknown view",
            exc,
        )
        original_detail = response.data
        response.data = {
            "error": {
                "code": response.status_code,
                "message": exc.__class__.__name__,
                "detail": original_detail,
            }
        }
    return response
