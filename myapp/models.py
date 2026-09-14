import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


# --- Base Abstract Models --------------------------------------------------
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDPrimaryKeyModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


# --- Accounts Models -------------------------------------------------------
class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields["role"] = "admin"
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        CRM = "CRM", "CRM Agent"

    phone = models.CharField(max_length=20, blank=True, default="")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CRM)

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"

    def save(self, *args, **kwargs):
        if self.is_superuser and self.role != self.Role.ADMIN:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username


class Agent(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_profile")
    display_name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    max_active_leads = models.PositiveIntegerField(default=50)
    last_assigned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_agent"
        ordering = ["display_name"]

    def __str__(self):
        return self.display_name


class PasswordResetOTP(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="password_otps")
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "accounts_password_reset_otp"
        ordering = ["-created_at"]

    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"OTP for {self.email} ({self.otp_code})"


# --- Phone Normalization Helper -------------------------------------------
def normalize_indian_mobile(raw_phone: str) -> str:
    cleaned = "".join(c for c in str(raw_phone) if c.isdigit())
    if len(cleaned) == 10:
        return f"+91{cleaned}"
    elif len(cleaned) == 12 and cleaned.startswith("91"):
        return f"+{cleaned}"
    elif len(cleaned) > 10 and not raw_phone.startswith("+"):
        return f"+{cleaned}"
    return raw_phone if raw_phone.startswith("+") else f"+{cleaned}"


# --- Leads Models ----------------------------------------------------------
class Lead(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = "New", "New"
        CONTACTED = "Contacted", "Contacted"
        QUALIFIED = "Qualified", "Qualified"
        NEEDS_HUMAN = "Needs Human Follow-up", "Needs Human Follow-up"
        FOLLOWUP_SCHEDULED = "Follow-up Scheduled", "Follow-up Scheduled"
        CONVERTED = "Converted", "Converted"
        LOST = "Lost", "Lost"

    class RequirementType(models.TextChoices):
        BUY = "Buy", "Buy"
        SELL = "Sell", "Sell"
        RENT = "Rent", "Rent"

    class InterestLevel(models.TextChoices):
        HIGH = "High", "High"
        MEDIUM = "Medium", "Medium"
        LOW = "Low", "Low"

    class Source(models.TextChoices):
        AI_CALL = "AI Call", "AI Call"
        MANUAL = "Manual", "Manual"
        WEBSITE = "Website", "Website"

    display_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=150)
    mobile = models.CharField(max_length=20, unique=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.AI_CALL)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW)

    requirement_type = models.CharField(max_length=10, choices=RequirementType.choices)
    property_type = models.CharField(max_length=50)
    budget_min = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=150)
    timeline = models.CharField(max_length=100, blank=True, default="")

    interest_level = models.CharField(max_length=10, choices=InterestLevel.choices, blank=True, default="")
    assigned_to = models.ForeignKey(
        Agent, null=True, blank=True, on_delete=models.SET_NULL, related_name="leads"
    )

    last_activity_at = models.DateTimeField(null=True, blank=True)
    next_follow_up_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leads_lead"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["mobile"])]

    def save(self, *args, **kwargs):
        if self.mobile:
            self.mobile = normalize_indian_mobile(self.mobile)
        if not self.display_id:
            self.display_id = self._generate_display_id()
        super().save(*args, **kwargs)

    def _generate_display_id(self):
        last = Lead.objects.order_by("-id").first()
        next_seq = (last.id if last else 1041) + 1
        return f"LD-{next_seq}"

    def __str__(self):
        return f"{self.display_id} — {self.name}"


class LeadActivity(TimeStampedModel):
    class ActivityType(models.TextChoices):
        STATUS_CHANGE = "status_change", "Status change"
        ASSIGNMENT = "assignment", "Assignment"
        CALL_LOGGED = "call_logged", "Call logged"
        NOTE = "note", "Note"
        WHATSAPP_SENT = "whatsapp_sent", "WhatsApp sent"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=30, choices=ActivityType.choices)
    description = models.CharField(max_length=255)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="lead_activities"
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "leads_leadactivity"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.lead.display_id}: {self.description}"


# --- Calls Models ----------------------------------------------------------
class Call(TimeStampedModel):
    class Direction(models.TextChoices):
        INBOUND = "Inbound", "Inbound"
        OUTBOUND = "Outbound", "Outbound"

    class Status(models.TextChoices):
        RINGING = "Ringing", "Ringing"
        IN_PROGRESS = "In Progress", "In Progress"
        COMPLETED = "Completed", "Completed"
        FAILED = "Failed", "Failed"
        NO_ANSWER = "No Answer", "No Answer"

    display_id = models.CharField(max_length=20, unique=True, editable=False)
    lead = models.ForeignKey(Lead, null=True, blank=True, on_delete=models.SET_NULL, related_name="calls")

    provider = models.CharField(max_length=30, default="exotel")
    provider_call_sid = models.CharField(max_length=100, unique=True, null=True, blank=True)
    voice_conversation_id = models.CharField(max_length=120, blank=True, default="", db_index=True)

    direction = models.CharField(max_length=10, choices=Direction.choices, default=Direction.INBOUND)
    from_number = models.CharField(max_length=20)
    to_number = models.CharField(max_length=20, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RINGING)

    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_sec = models.PositiveIntegerField(default=0)

    recording_url = models.URLField(blank=True, default="")

    class Meta:
        db_table = "calls_call"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["from_number"])]

    def save(self, *args, **kwargs):
        if not self.display_id:
            last = Call.objects.order_by("-id").first()
            next_seq = (last.id if last else 5223) + 1
            self.display_id = f"CL-{next_seq}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_id


class CallEvent(TimeStampedModel):
    class EventType(models.TextChoices):
        INCOMING_CALL = "incoming_call", "Incoming Call"
        STATUS_UPDATE = "status_update", "Status Update"
        AI_CONVERSED = "ai_conversed", "AI Conversed"

    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=50, choices=EventType.choices, default=EventType.INCOMING_CALL)
    payload = models.JSONField(default=dict, blank=True)
    provider_event_id = models.CharField(max_length=128, null=True, blank=True, unique=True)

    class Meta:
        db_table = "calls_callevent"
        ordering = ["created_at"]


class CallTranscript(TimeStampedModel):
    call = models.OneToOneField(Call, on_delete=models.CASCADE, related_name="transcript")
    turns = models.JSONField(default=list, blank=True)
    full_text = models.TextField(blank=True, default="")

    class Meta:
        db_table = "calls_calltranscript"

    def __str__(self):
        return f"Transcript for {self.call.display_id}"


class CallSummary(TimeStampedModel):
    class InterestLevel(models.TextChoices):
        HIGH = "High", "High"
        MEDIUM = "Medium", "Medium"
        LOW = "Low", "Low"

    call = models.OneToOneField(Call, on_delete=models.CASCADE, related_name="summary")
    requirement = models.CharField(max_length=255, blank=True, default="")
    budget_text = models.CharField(max_length=100, blank=True, default="")
    location = models.CharField(max_length=150, blank=True, default="")
    interest_level = models.CharField(max_length=10, choices=InterestLevel.choices, blank=True, default="")
    key_points = models.JSONField(default=list, blank=True)
    suggested_action = models.CharField(max_length=255, blank=True, default="")
    follow_up_date = models.DateTimeField(null=True, blank=True)
    generated_by = models.CharField(max_length=50, default="llm")

    class Meta:
        db_table = "calls_callsummary"

    def __str__(self):
        return f"Summary for {self.call.display_id}"


# --- AI Models -------------------------------------------------------------
class AISession(TimeStampedModel):
    class Stage(models.TextChoices):
        START = "START", "Start"
        GREETING = "GREETING", "Greeting"
        INTENT = "INTENT", "Intent (Buy/Sell/Rent)"
        PROPERTY_TYPE = "PROPERTY_TYPE", "Property type"
        BUDGET = "BUDGET", "Budget"
        LOCATION = "LOCATION", "Location"
        TIMELINE = "TIMELINE", "Timeline"
        CONFIRMATION = "CONFIRMATION", "Confirmation"
        COMPLETE = "COMPLETE", "Complete"
        HUMAN_HANDOFF = "HUMAN_HANDOFF", "Human handoff"

    call = models.OneToOneField(Call, on_delete=models.CASCADE, related_name="ai_session")
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.START)
    clarify_attempts = models.PositiveSmallIntegerField(default=0)
    extracted_fields = models.JSONField(default=dict, blank=True)
    ended_reason = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "ai_app_aisession"

    def __str__(self):
        return f"AISession({self.call.display_id}) @ {self.stage}"


# --- Followup Models -------------------------------------------------------
class Followup(TimeStampedModel):
    class FollowupType(models.TextChoices):
        CALL = "Call", "Call"
        WHATSAPP = "WhatsApp", "WhatsApp"
        EMAIL = "Email", "Email"
        SITE_VISIT = "Site Visit", "Site Visit"

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        COMPLETED = "Completed", "Completed"
        MISSED = "Missed", "Missed"

    display_id = models.CharField(max_length=20, unique=True, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="followups")
    assigned_to = models.ForeignKey(Agent, null=True, blank=True, on_delete=models.SET_NULL, related_name="followups")

    followup_type = models.CharField(max_length=20, choices=FollowupType.choices, default=FollowupType.CALL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    note = models.CharField(max_length=255, blank=True, default="")
    due_at = models.DateTimeField()

    class Meta:
        db_table = "followups_followup"
        ordering = ["due_at"]
        indexes = [models.Index(fields=["status", "due_at"])]

    def save(self, *args, **kwargs):
        if not self.display_id:
            last = Followup.objects.order_by("-id").first()
            next_seq = (last.id if last else 894) + 1
            self.display_id = f"FU-{next_seq}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.display_id} for {self.lead.display_id}"


# --- WhatsApp Models -------------------------------------------------------
class WhatsAppMessage(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "Queued", "Queued"
        SENT = "Sent", "Sent"
        DELIVERED = "Delivered", "Delivered"
        READ = "Read", "Read"
        FAILED = "Failed", "Failed"

    display_id = models.CharField(max_length=20, unique=True, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="whatsapp_messages")
    call = models.ForeignKey(Call, null=True, blank=True, on_delete=models.SET_NULL, related_name="whatsapp_messages")

    to_number = models.CharField(max_length=20)
    template_name = models.CharField(max_length=100)
    body = models.TextField()

    provider_message_id = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    failure_reason = models.CharField(max_length=255, blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "whatsapp_whatsappmessage"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.display_id:
            last = WhatsAppMessage.objects.order_by("-id").first()
            next_seq = (last.id if last else 3295) + 1
            self.display_id = f"WA-{next_seq}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.display_id} -> {self.to_number} ({self.status})"


# --- Audit Models ----------------------------------------------------------
class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    actor_label = models.CharField(max_length=64, default="system")
    action = models.CharField(max_length=64)
    object_type = models.CharField(max_length=64)
    object_id = models.CharField(max_length=64, blank=True, default="")
    method = models.CharField(max_length=8, blank=True, default="")
    path = models.CharField(max_length=255, blank=True, default="")
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_auditlog"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["object_type", "object_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.action} {self.object_type}:{self.object_id} by {self.actor_label}"


# --- Application Info Model -----------------------------------------------
class ApplicationInfo(models.Model):
    name = models.CharField(max_length=120, default="Anpurna Properties")
    app_name = models.CharField(max_length=80, default="anpurna")

    class Meta:
        db_table = "anpurna_applicationinfo"
        verbose_name = "Application Info"
        verbose_name_plural = "Application Info"

    def __str__(self):
        return self.name
