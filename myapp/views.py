import hashlib
import json
import logging
import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
# pyrefly: ignore [missing-import]
from rest_framework_simplejwt.tokens import RefreshToken

from . import services
from .filters import LeadFilter
from .models import Agent, Call, CallEvent, Followup, Lead, PasswordResetOTP, User, WhatsAppMessage
from .permissions import IsStaffOrReadOnly
from .serializers import (
    AgentSerializer, CallSerializer, CallStatusWebhookSerializer, CallSummarySerializer,
    CallTranscriptSerializer, ChangePasswordSerializer, FollowupSerializer, IncomingCallWebhookSerializer,
    LeadActivitySerializer, LeadDetailSerializer, LeadReadSerializer, LeadWriteSerializer,
    LoginSerializer, ResetPasswordConfirmSerializer, ResetPasswordRequestSerializer, SignupSerializer,
    UserSerializer, WhatsAppMessageSerializer
)
from .webhook_auth import verify_exotel_signature

logger = logging.getLogger("anpurna_properties")


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


# --- Accounts Views --------------------------------------------------------
class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class AgentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Agent.objects.filter(is_active=True)
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response({
            "message": "User registered successfully",
            "tokens": tokens,
            "user": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email_or_username = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        username = email_or_username
        user_obj = User.objects.filter(Q(email__iexact=email_or_username) | Q(username__iexact=email_or_username)).first()
        if user_obj:
            username = user_obj.username

        user = authenticate(username=username, password=password)
        if not user:
            return Response({"error": "Invalid email or password"}, status=status.HTTP_400_BAD_REQUEST)

        tokens = get_tokens_for_user(user)
        return Response({
            "message": "Login successful",
            "tokens": tokens,
            "user": UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": ["Incorrect current password"]}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data["new_password"])
        user.save()
        tokens = get_tokens_for_user(user)
        return Response({"message": "Password changed successfully", "tokens": tokens}, status=status.HTTP_200_OK)


class ResetPasswordRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email_or_identifier = serializer.validated_data["email"].strip()
        user = User.objects.filter(Q(email__iexact=email_or_identifier) | Q(username__iexact=email_or_identifier)).first()
        
        if not user:
            return Response({"error": f"No registered user found with email or username '{email_or_identifier}'."}, status=status.HTTP_400_BAD_REQUEST)

        PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)

        otp_code = f"{random.randint(100000, 999999)}"
        expires_at = timezone.now() + timedelta(minutes=15)
        recipient_email = user.email or email_or_identifier

        PasswordResetOTP.objects.create(
            user=user,
            email=recipient_email,
            otp_code=otp_code,
            expires_at=expires_at
        )

        subject = "Your Password Reset OTP — Annapurna Pro"
        message = (
            f"Hello {user.first_name or user.username},\n\n"
            f"Your 6-digit OTP to reset your password is: {otp_code}\n\n"
            f"This OTP is valid for 15 minutes. If you did not request a password reset, please ignore this email."
        )

        # Print OTP to console for instant visibility
        print(f"\n=======================================================", flush=True)
        print(f"[PASSWORD RESET OTP] Email/User: {recipient_email} | OTP: {otp_code}", flush=True)
        print(f"=======================================================\n", flush=True)
        logger.info("[PASSWORD RESET OTP] Email: %s | OTP: %s", recipient_email, otp_code)

        try:
            send_mail(
                subject,
                message,
                getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@annapurnapro.com"),
                [recipient_email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.error("Failed to send OTP email to %s: %s", recipient_email, exc)

        return Response({
            "message": f"6-digit OTP generated successfully. OTP sent to {recipient_email}",
            "email": recipient_email
        }, status=status.HTTP_200_OK)


class ResetPasswordConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        otp_code = serializer.validated_data["otp_code"].strip()
        new_password = serializer.validated_data["new_password"]

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({"error": "Invalid email or OTP code"}, status=status.HTTP_400_BAD_REQUEST)

        otp_record = PasswordResetOTP.objects.filter(
            user=user,
            email__iexact=email,
            otp_code=otp_code,
            is_used=False,
            expires_at__gt=timezone.now()
        ).first()

        if not otp_record:
            return Response({"error": "Invalid or expired OTP code"}, status=status.HTTP_400_BAD_REQUEST)

        otp_record.is_used = True
        otp_record.save(update_fields=["is_used", "updated_at"])

        user.set_password(new_password)
        user.save()

        return Response({
            "message": "Password reset successfully. You can now login with your new password."
        }, status=status.HTTP_200_OK)


# --- Leads Views -----------------------------------------------------------
class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all().select_related("assigned_to")
    permission_classes = [IsStaffOrReadOnly]
    filterset_class = LeadFilter
    search_fields = ["name", "mobile", "location", "display_id"]
    ordering_fields = ["created_at", "last_activity_at", "status"]
    lookup_field = "display_id"

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return LeadWriteSerializer
        if self.action == "retrieve":
            return LeadDetailSerializer
        return LeadReadSerializer

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        lead = serializer.save()
        if serializer.validated_data.get("status") and serializer.validated_data["status"] != old_status:
            services.change_status(lead, lead.status, actor=self.request.user)

    @action(detail=True, methods=["get"])
    def activities(self, request, display_id=None):
        lead = self.get_object()
        serializer = LeadActivitySerializer(lead.activities.all(), many=True)
        return Response(serializer.data)


# --- Calls Views -----------------------------------------------------------
class CallViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Call.objects.all().select_related("lead", "summary")
    serializer_class = CallSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "direction", "lead"]
    search_fields = ["display_id", "from_number", "provider_call_sid"]
    ordering_fields = ["created_at", "started_at", "duration_sec"]
    lookup_field = "display_id"

    @action(detail=True, methods=["get"])
    def transcript(self, request, display_id=None):
        call = self.get_object()
        if not hasattr(call, "transcript"):
            return Response({"detail": "Transcript not available yet"}, status=404)
        return Response(CallTranscriptSerializer(call.transcript).data)

    @action(detail=True, methods=["get"])
    def summary(self, request, display_id=None):
        call = self.get_object()
        if not hasattr(call, "summary"):
            return Response({"detail": "Summary not available yet"}, status=404)
        return Response(CallSummarySerializer(call.summary).data)


# --- Telephony Webhooks ----------------------------------------------------
def _event_id(request, prefix):
    supplied = request.headers.get("X-Exotel-Event-Id") or request.data.get("event_id")
    if supplied:
        return f"{prefix}:{supplied}"
    try:
        raw = request.body
    except Exception:
        raw = None
    if not raw:
        raw = json.dumps(request.data, sort_keys=True, default=str).encode()
    return f"{prefix}:sha256:{hashlib.sha256(raw).hexdigest()}"


def _incoming_payload(data):
    return {
        "call_sid": data.get("call_sid") or data.get("CallSid") or data.get("callsid"),
        "from_number": data.get("from_number") or data.get("From") or data.get("from"),
        "to_number": data.get("to_number") or data.get("To") or data.get("to") or "",
        "direction": data.get("direction") if data.get("direction") in {"Inbound", "Outbound"} else "Inbound",
        "started_at": data.get("started_at"),
    }


def _status_payload(data):
    raw = (data.get("status") or data.get("Status") or data.get("CallStatus") or "").lower().replace("_", "-")
    status_map = {"ringing": "Ringing", "in-progress": "In Progress", "in progress": "In Progress", "answered": "In Progress", "completed": "Completed", "failed": "Failed", "busy": "Failed", "no-answer": "No Answer", "no answer": "No Answer"}
    return {
        "call_sid": data.get("call_sid") or data.get("CallSid") or data.get("callsid"),
        "status": status_map.get(raw, data.get("status")),
        "duration_sec": data.get("duration_sec") or data.get("Duration") or data.get("duration") or 0,
        "recording_url": data.get("recording_url") or data.get("RecordingUrl") or data.get("recordingurl") or "",
        "ended_at": data.get("ended_at"),
    }


class IncomingCallWebhookView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "webhooks"

    def post(self, request):
        if not verify_exotel_signature(request):
            return Response({"error": "invalid signature"}, status=401)

        serializer = IncomingCallWebhookSerializer(data=_incoming_payload(request.data))
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        call, created = Call.objects.get_or_create(
            provider_call_sid=data["call_sid"],
            defaults={
                "direction": data.get("direction", "Inbound"),
                "from_number": data["from_number"],
                "to_number": data.get("to_number", ""),
                "status": Call.Status.IN_PROGRESS,
                "started_at": data.get("started_at") or timezone.now(),
            },
        )
        event_id = _event_id(request, "incoming")
        event, event_created = CallEvent.objects.get_or_create(
            provider_event_id=event_id,
            defaults={"call": call, "event_type": "incoming_call", "payload": dict(request.data)}
        )
        if not event_created:
            return Response({"call_id": call.display_id, "status": call.status, "duplicate": True}, status=200)

        if created:
            from myapp.tasks import start_ai_conversation
            start_ai_conversation.delay(str(call.id))
            logger.info("Queued AI conversation for call %s", call.display_id)

        return Response({"call_id": call.display_id, "status": call.status}, status=201)


class CallStatusWebhookView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "webhooks"

    def post(self, request):
        if not verify_exotel_signature(request):
            return Response({"error": "invalid signature"}, status=401)

        serializer = CallStatusWebhookSerializer(data=_status_payload(request.data))
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            call = Call.objects.get(provider_call_sid=data["call_sid"])
        except Call.DoesNotExist:
            call = Call.objects.create(
                provider_call_sid=data["call_sid"],
                from_number="unknown",
                status=Call.Status.RINGING,
            )

        event_id = _event_id(request, "status")
        if CallEvent.objects.filter(provider_event_id=event_id).exists():
            return Response({"call_id": call.display_id, "status": call.status, "duplicate": True})
        
        already_completed = call.status == Call.Status.COMPLETED
        call.status = data["status"]
        call.duration_sec = data.get("duration_sec", call.duration_sec)
        call.recording_url = data.get("recording_url", call.recording_url)
        call.ended_at = data.get("ended_at") or timezone.now()
        call.save()
        CallEvent.objects.create(call=call, event_type="status_update", payload=dict(request.data), provider_event_id=event_id)

        if data["status"] == Call.Status.COMPLETED and not already_completed:
            from myapp.tasks import finalize_completed_call
            finalize_completed_call.delay(str(call.id))
        elif data["status"] == Call.Status.FAILED:
            logger.info("Call %s failed/undelivered — logged, no lead pipeline triggered", call.display_id)

        return Response({"call_id": call.display_id, "status": call.status})


# --- Followups Views ------------------------------------------------------
class FollowupViewSet(viewsets.ModelViewSet):
    queryset = Followup.objects.all().select_related("lead", "assigned_to")
    serializer_class = FollowupSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "followup_type", "assigned_to", "lead"]
    search_fields = ["display_id", "note", "lead__name", "lead__display_id"]
    ordering_fields = ["due_at", "created_at"]
    lookup_field = "display_id"


# --- WhatsApp Views --------------------------------------------------------
class WhatsAppMessageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WhatsAppMessage.objects.all().select_related("lead", "call")
    serializer_class = WhatsAppMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "lead", "call"]
    search_fields = ["display_id", "to_number", "provider_message_id"]
    ordering_fields = ["created_at", "sent_at"]
    lookup_field = "display_id"

    @action(detail=True, methods=["post"])
    def resend(self, request, display_id=None):
        message = self.get_object()
        services.resend_whatsapp(message)
        return Response(WhatsAppMessageSerializer(message).data)


# --- Dashboard Views -------------------------------------------------------
class DashboardMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        total_leads = Lead.objects.count()
        leads_today = Lead.objects.filter(created_at__gte=today_start).count()
        qualified = Lead.objects.filter(status=Lead.Status.QUALIFIED).count()
        needs_human = Lead.objects.filter(status=Lead.Status.NEEDS_HUMAN).count()

        calls_total = Call.objects.count()
        calls_today = Call.objects.filter(created_at__gte=today_start).count()
        completed_calls = Call.objects.filter(status=Call.Status.COMPLETED).count()

        wa_sent = WhatsAppMessage.objects.filter(status=WhatsAppMessage.Status.SENT).count()
        wa_failed = WhatsAppMessage.objects.filter(status=WhatsAppMessage.Status.FAILED).count()
        pending_followups = Followup.objects.filter(status=Followup.Status.PENDING).count()

        leads_by_status = dict(
            Lead.objects.values("status").annotate(c=Count("id")).values_list("status", "c")
        )

        return Response({
            "overview": {
                "total_leads": total_leads,
                "leads_today": leads_today,
                "qualified_leads": qualified,
                "needs_human_followup": needs_human,
                "total_calls": calls_total,
                "calls_today": calls_today,
                "completed_calls": completed_calls,
                "whatsapp_sent": wa_sent,
                "whatsapp_failed": wa_failed,
                "pending_followups": pending_followups,
            },
            "leads_by_status": leads_by_status,
        })
