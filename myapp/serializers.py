from rest_framework import serializers
from .models import (
    User, Agent, Lead, LeadActivity, Call, CallTranscript, CallSummary,
    Followup, WhatsAppMessage
)


# --- Accounts Serializers --------------------------------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "phone", "role"]
        read_only_fields = ["id"]


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "first_name", "last_name", "phone", "role"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        if user.role == User.Role.CRM:
            Agent.objects.get_or_create(
                user=user,
                defaults={"display_name": user.get_full_name() or user.username}
            )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True, help_text="Email address or username")
    password = serializers.CharField(write_only=True, required=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6)


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.CharField(required=True, help_text="Email address or username")


class ResetPasswordConfirmSerializer(serializers.Serializer):
    email = serializers.CharField(required=True, help_text="Email address or username")
    otp_code = serializers.CharField(required=True, min_length=6, max_length=6)
    new_password = serializers.CharField(required=True, min_length=6)


class AgentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Agent
        fields = ["id", "display_name", "username", "email", "is_active", "max_active_leads"]


# --- Leads Serializers -----------------------------------------------------
class LeadReadSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source="assigned_to.display_name", read_only=True, default="Unassigned")
    budget_formatted = serializers.SerializerMethodField()
    requirement_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id", "display_id", "name", "mobile", "source", "status",
            "requirement_type", "property_type", "requirement_formatted",
            "budget_min", "budget_max", "budget_formatted",
            "location", "timeline", "interest_level", "assigned_to", "assigned_to_name",
            "created_at", "last_activity_at", "next_follow_up_at"
        ]

    def get_budget_formatted(self, obj):
        def _fmt(amt):
            if not amt:
                return ""
            val = float(amt)
            if val >= 10000000:
                c = val / 10000000
                return f"₹{c:.2f}".rstrip("0").rstrip(".") + "Cr"
            elif val >= 100000:
                l = val / 100000
                return f"₹{l:.2f}".rstrip("0").rstrip(".") + "L"
            else:
                return f"₹{val:,.0f}"

        if obj.budget_min and obj.budget_max:
            return f"{_fmt(obj.budget_min)} - {_fmt(obj.budget_max)}"
        elif obj.budget_min:
            return f"> {_fmt(obj.budget_min)}"
        elif obj.budget_max:
            return f"< {_fmt(obj.budget_max)}"
        return "Not specified"

    def get_requirement_formatted(self, obj):
        parts = [p for p in [obj.requirement_type, obj.property_type] if p]
        return " · ".join(parts) if parts else ""


class LeadActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True, default="system")

    class Meta:
        model = LeadActivity
        fields = ["id", "activity_type", "description", "actor_name", "metadata", "created_at"]


class LeadDetailSerializer(LeadReadSerializer):
    activities = LeadActivitySerializer(many=True, read_only=True)

    class Meta(LeadReadSerializer.Meta):
        fields = LeadReadSerializer.Meta.fields + ["activities"]


class LeadWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            "id", "display_id", "name", "mobile", "source", "status", "requirement_type",
            "property_type", "budget_min", "budget_max", "location",
            "timeline", "interest_level", "assigned_to", "created_at"
        ]
        read_only_fields = ["id", "display_id", "created_at"]

    def validate(self, attrs):
        b_min = attrs.get("budget_min")
        b_max = attrs.get("budget_max")
        if b_min and b_max and b_min > b_max:
            raise serializers.ValidationError("budget_min cannot be greater than budget_max.")
        return attrs


# --- Calls Serializers -----------------------------------------------------
class CallSummarySerializer(serializers.ModelSerializer):
    call = serializers.CharField(source="call.display_id", read_only=True)

    class Meta:
        model = CallSummary
        fields = ["call", "requirement", "budget_text", "location", "interest_level", "key_points", "suggested_action", "follow_up_date", "generated_by"]


class CallTranscriptSerializer(serializers.ModelSerializer):
    call = serializers.CharField(source="call.display_id", read_only=True)

    class Meta:
        model = CallTranscript
        fields = ["call", "turns", "full_text"]


class CallSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.name", read_only=True, default="Unknown Caller")
    summary = CallSummarySerializer(read_only=True)
    duration_formatted = serializers.SerializerMethodField()
    recording_status = serializers.SerializerMethodField()

    class Meta:
        model = Call
        fields = [
            "id", "display_id", "lead", "lead_name", "provider", "provider_call_sid",
            "direction", "from_number", "to_number", "status",
            "started_at", "ended_at", "duration_sec", "duration_formatted",
            "recording_url", "recording_status", "summary", "created_at"
        ]

    def get_duration_formatted(self, obj):
        sec = obj.duration_sec or 0
        m, s = divmod(sec, 60)
        return f"{m}:{s:02d}"

    def get_recording_status(self, obj):
        return "Available" if obj.recording_url else "Not available"


# --- Telephony Webhook Serializers ----------------------------------------
class IncomingCallWebhookSerializer(serializers.Serializer):
    call_sid = serializers.CharField()
    from_number = serializers.CharField()
    to_number = serializers.CharField(required=False, allow_blank=True)
    direction = serializers.ChoiceField(choices=["Inbound", "Outbound"], default="Inbound")
    started_at = serializers.DateTimeField(required=False, allow_null=True)


class CallStatusWebhookSerializer(serializers.Serializer):
    call_sid = serializers.CharField()
    status = serializers.ChoiceField(choices=["Ringing", "In Progress", "Completed", "Failed", "No Answer"])
    duration_sec = serializers.IntegerField(required=False, default=0)
    recording_url = serializers.URLField(required=False, allow_blank=True)
    ended_at = serializers.DateTimeField(required=False, allow_null=True)


# --- Followup Serializers -------------------------------------------------
class FollowupSerializer(serializers.ModelSerializer):
    lead_display_id = serializers.CharField(source="lead.display_id", read_only=True)
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.display_name", read_only=True, default="")

    class Meta:
        model = Followup
        fields = [
            "id", "display_id", "lead", "lead_display_id", "lead_name",
            "assigned_to", "assigned_to_name", "followup_type", "status",
            "note", "due_at", "created_at"
        ]


# --- WhatsApp Serializers --------------------------------------------------
class WhatsAppMessageSerializer(serializers.ModelSerializer):
    lead_display_id = serializers.CharField(source="lead.display_id", read_only=True)
    lead_name = serializers.CharField(source="lead.name", read_only=True, default="Unknown Customer")

    class Meta:
        model = WhatsAppMessage
        fields = [
            "id", "display_id", "lead", "lead_display_id", "lead_name", "call", "to_number",
            "template_name", "body", "provider_message_id", "status",
            "failure_reason", "sent_at", "created_at"
        ]
