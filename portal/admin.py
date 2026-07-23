from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q

from .models import CivicReport, AuditLog, HotspotAnalysis, AdminSettings


# ===========================================================================
# CivicReport Admin
# ===========================================================================
@admin.register(CivicReport)
class CivicReportAdmin(admin.ModelAdmin):
    """Advanced admin interface for civic reports with filtering and actions."""

    list_display = [
        "priority_badge",
        "issue",
        "location",
        "confidence",
        "status_badge",
        "upvotes",
        "submitted_at",
    ]
    list_filter = [
        "priority",
        "issue",
        "status",
        "confidence",
        ("submitted_at", admin.DateFieldListFilter),
    ]
    search_fields = ["description", "location", "department"]
    readonly_fields = [
        "risk_score",
        "submitted_at",
        "updated_at",
        "resolved_at",
    ]

    fieldsets = (
        (
            "Report Details",
            {
                "fields": (
                    "description",
                    "location",
                    "photo",
                )
            },
        ),
        (
            "AI Classification",
            {
                "fields": (
                    "issue",
                    "priority",
                    "department",
                    "confidence",
                    "risk_score",
                    "reason",
                    "advice",
                    "suggested_action",
                )
            },
        ),
        (
            "Community Engagement",
            {
                "fields": (
                    "upvotes",
                )
            },
        ),
        (
            "Moderation",
            {
                "fields": (
                    "status",
                    "moderator_notes",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "ip_address",
                    "device_id",
                    "submitted_at",
                    "updated_at",
                    "resolved_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["mark_as_spam", "mark_as_valid", "mark_as_pending", "mark_resolved"]

    def priority_badge(self, obj):
        """Display priority as a colored badge."""
        colors = {
            "Critical": "red",
            "High": "orange",
            "Medium": "blue",
            "Low": "green",
        }
        color = colors.get(obj.priority, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.priority,
        )

    priority_badge.short_description = "Priority"

    def status_badge(self, obj):
        """Display status as a colored badge."""
        status_map = {0: ("Valid", "green"), 1: ("Spam", "red"), 2: ("Pending", "orange")}
        label, color = status_map.get(obj.status, ("Unknown", "gray"))
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            label,
        )

    status_badge.short_description = "Status"

    def mark_as_spam(self, request, queryset):
        """Bulk action: Mark reports as spam."""
        updated = queryset.update(status=1)
        self.message_user(request, f"{updated} reports marked as spam.")

    mark_as_spam.short_description = "Mark selected as spam"

    def mark_as_valid(self, request, queryset):
        """Bulk action: Mark reports as valid."""
        updated = queryset.update(status=0)
        self.message_user(request, f"{updated} reports marked as valid.")

    mark_as_valid.short_description = "Mark selected as valid"

    def mark_as_pending(self, request, queryset):
        """Bulk action: Mark reports as pending review."""
        updated = queryset.update(status=2)
        self.message_user(request, f"{updated} reports marked as pending.")

    mark_as_pending.short_description = "Mark selected as pending review"

    def mark_resolved(self, request, queryset):
        """Bulk action: Mark issues as resolved."""
        from django.utils import timezone
        updated = queryset.update(resolved_at=timezone.now())
        self.message_user(request, f"{updated} reports marked as resolved.")

    mark_resolved.short_description = "Mark selected as resolved"


# ===========================================================================
# AuditLog Admin
# ===========================================================================
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only admin for audit logs."""

    list_display = ["action", "admin_username", "ip_address", "created_at"]
    list_filter = ["action", ("created_at", admin.DateFieldListFilter)]
    search_fields = ["admin_username", "ip_address"]
    readonly_fields = ["action", "admin_username", "ip_address", "details", "created_at"]

    def has_add_permission(self, request):
        """Prevent manual creation of audit logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of audit logs."""
        return False


# ===========================================================================
# HotspotAnalysis Admin
# ===========================================================================
@admin.register(HotspotAnalysis)
class HotspotAnalysisAdmin(admin.ModelAdmin):
    """Admin for geographic hotspot analysis."""

    list_display = ["location", "issue_type", "report_count", "avg_risk_score", "last_updated"]
    list_filter = ["issue_type", ("last_updated", admin.DateFieldListFilter)]
    search_fields = ["location", "issue_type"]
    readonly_fields = ["last_updated"]

    fieldsets = (
        (
            "Location",
            {
                "fields": ("location", "latitude", "longitude")
            },
        ),
        (
            "Analysis",
            {
                "fields": (
                    "issue_type",
                    "report_count",
                    "avg_risk_score",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": ("last_updated",),
                "classes": ("collapse",),
            },
        ),
    )


# ===========================================================================
# AdminSettings Admin
# ===========================================================================
@admin.register(AdminSettings)
class AdminSettingsAdmin(admin.ModelAdmin):
    """Admin for system-wide settings."""

    list_display = ["key", "value", "updated_by", "updated_at"]
    list_filter = [("updated_at", admin.DateFieldListFilter)]
    search_fields = ["key", "description"]
    readonly_fields = ["updated_at"]

    fieldsets = (
        (
            "Setting",
            {
                "fields": ("key", "value", "description")
            },
        ),
        (
            "History",
            {
                "fields": ("updated_by", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        """Track who changed the setting."""
        obj.updated_by = request.user.username
        super().save_model(request, obj, form, change)
