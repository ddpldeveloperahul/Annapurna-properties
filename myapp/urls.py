from django.urls import include, path
# pyrefly: ignore [missing-import]
from rest_framework.routers import DefaultRouter
# pyrefly: ignore [missing-import]
from rest_framework_simplejwt.views import TokenRefreshView


# pyrefly: ignore [missing-import]
from .views import AccountViewSet, AgentViewSet, CallStatusWebhookView, CallViewSet,ChangePasswordView, DashboardMetricsView, FollowupViewSet, IncomingCallWebhookView, LeadViewSet,LoginView, LogoutView, MeView, ResetPasswordConfirmView, ResetPasswordRequestView,SignupView, WhatsAppMessageViewSet


router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("agents", AgentViewSet, basename="agent")
router.register("leads", LeadViewSet, basename="lead")
router.register("calls", CallViewSet, basename="call")
router.register("followups", FollowupViewSet, basename="followup")
router.register("whatsapp", WhatsAppMessageViewSet, basename="whatsapp")

urlpatterns = [
    path("", include(router.urls)),
    path("me/", MeView.as_view(), name="user-me"),
    path("auth/signup/", SignupView.as_view(), name="auth-signup"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("auth/reset-password/", ResetPasswordRequestView.as_view(), name="auth-reset-password-request"),
    path("auth/reset-password/confirm/", ResetPasswordConfirmView.as_view(), name="auth-reset-password-confirm"),



    #dashboard api 
    path("dashboard/metrics/", DashboardMetricsView.as_view(), name="dashboard-metrics"),
    path("telephony/webhooks/incoming-call/", IncomingCallWebhookView.as_view(), name="webhook-incoming-call"),
    path("telephony/webhooks/call-status/", CallStatusWebhookView.as_view(), name="webhook-call-status"),




]
