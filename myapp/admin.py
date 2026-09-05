from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Agent, PasswordResetOTP, Lead, LeadActivity, Call, CallEvent, CallTranscript,
    CallSummary, AISession, Followup, WhatsAppMessage, AuditLog, ApplicationInfo
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("CRM Profile", {"fields": ("phone", "role")}),
    )
    list_display = ["username", "email", "first_name", "last_name", "role", "is_staff"]


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ["display_name", "user", "is_active", "max_active_leads"]
    list_filter = ["is_active"]


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ["email", "otp_code", "is_used", "expires_at", "created_at"]
    list_filter = ["is_used"]
    search_fields = ["email", "otp_code"]


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["display_id", "name", "mobile", "requirement_type", "property_type", "status", "assigned_to", "created_at"]
    list_filter = ["status", "requirement_type", "source", "interest_level"]
    search_fields = ["name", "mobile", "display_id", "location"]


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ["lead", "activity_type", "description", "actor", "created_at"]
    list_filter = ["activity_type"]


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ["display_id", "from_number", "status", "direction", "duration_sec", "created_at"]
    list_filter = ["status", "direction"]
    search_fields = ["display_id", "from_number", "provider_call_sid"]


@admin.register(CallEvent)
class CallEventAdmin(admin.ModelAdmin):
    list_display = ["call", "event_type", "provider_event_id", "created_at"]


@admin.register(CallTranscript)
class CallTranscriptAdmin(admin.ModelAdmin):
    list_display = ["call", "created_at"]


@admin.register(CallSummary)
class CallSummaryAdmin(admin.ModelAdmin):
    list_display = ["call", "requirement", "interest_level", "generated_by"]


@admin.register(AISession)
class AISessionAdmin(admin.ModelAdmin):
    list_display = ["call", "stage", "clarify_attempts", "created_at"]


@admin.register(Followup)
class FollowupAdmin(admin.ModelAdmin):
    list_display = ["display_id", "lead", "assigned_to", "followup_type", "status", "due_at"]
    list_filter = ["status", "followup_type"]


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ["display_id", "lead", "to_number", "status", "sent_at"]
    list_filter = ["status"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "object_type", "object_id", "actor_label", "created_at"]
    list_filter = ["action", "object_type"]


@admin.register(ApplicationInfo)
class ApplicationInfoAdmin(admin.ModelAdmin):
    list_display = ["name", "app_name"]
