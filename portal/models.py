from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

# ============================================================================
# CivicReport — Core model for civic issue reports
# ============================================================================
class CivicReport(models.Model):
    """
    Core data model for civic issue reports.
    Supports offline-first PWA with AI-powered triage.
    """

    # Priority levels
    PRIORITY_CHOICES = [
        ("Critical", "Critical - Immediate Action Required"),
        ("High", "High - Urgent"),
        ("Medium", "Medium - Standard"),
        ("Low", "Low - Maintenance"),
    ]

    # Issue categories
    ISSUE_CHOICES = [
        ("Road Damage", "Road Damage"),
        ("Water Leakage", "Water Leakage"),
        ("Garbage", "Garbage & Waste"),
        ("Electricity", "Electricity Hazard"),
        ("Streetlight", "Streetlight Failure"),
        ("Flood", "Flooding/Waterlogging"),
        ("Fire Emergency", "Fire Emergency"),
        ("Tree Fall", "Tree Fall/Obstruction"),
        ("General Civic Issue", "General Civic Issue"),
    ]

    # Report status
    STATUS_CHOICES = [
        (0, "Approved - Valid"),
        (1, "Flagged - Spam/Invalid"),
        (2, "Pending - Needs Review"),
    ]

    # Confidence levels
    CONFIDENCE_CHOICES = [
        ("High", "High (>75%)"),
        ("Medium", "Medium (50-75%)"),
        ("Low", "Low (<50%)"),
    ]

    # Core fields
    description = models.TextField(
        help_text="Detailed description of the civic issue"
    )
    location = models.CharField(
        max_length=255,
        default="Unknown",
        help_text="Location/address where the issue is reported",
    )

    # AI Classification fields
    issue = models.CharField(
        max_length=50,
        choices=ISSUE_CHOICES,
        default="General Civic Issue",
        help_text="AI-classified issue type",
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="Medium",
        help_text="Priority level from AI triage",
    )
    department = models.CharField(
        max_length=100,
        default="Municipal Corporation",
        help_text="Recommended responsible department",
    )
    confidence = models.CharField(
        max_length=20,
        choices=CONFIDENCE_CHOICES,
        default="Medium",
        help_text="AI confidence in classification",
    )

    # Risk & Analysis
    risk_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="0-100 risk severity score",
    )
    reason = models.TextField(
        blank=True,
        help_text="AI reasoning for classification",
    )
    advice = models.TextField(
        blank=True,
        help_text="AI-generated advice for the reporter",
    )
    suggested_action = models.TextField(
        blank=True,
        help_text="Suggested action for responsible department",
    )

    # Media & Evidence
    photo = models.ImageField(
        upload_to="reports/%Y/%m/%d/",
        null=True,
        blank=True,
        help_text="Photo evidence of the issue",
    )

    # Community engagement
    upvotes = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0)],
        help_text="Community support/verification count",
    )

    # Moderation
    status = models.IntegerField(
        choices=STATUS_CHOICES,
        default=0,
        help_text="Report moderation status (0=valid, 1=spam, 2=needs_review)",
    )
    moderator_notes = models.TextField(
        blank=True,
        help_text="Admin notes on moderation decision",
    )

    # Timestamps
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the report was submitted",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last modification timestamp",
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the issue was marked resolved",
    )

    # Metadata
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Reporter IP (for duplicate detection)",
    )
    device_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Device identifier (PWA offline support)",
    )

    class Meta:
        db_table = "portal_civic_report"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["-submitted_at"]),
            models.Index(fields=["issue", "-submitted_at"]),
            models.Index(fields=["priority", "-submitted_at"]),
            models.Index(fields=["status", "-submitted_at"]),
            models.Index(fields=["location", "-submitted_at"]),
        ]
        verbose_name = "Civic Report"
        verbose_name_plural = "Civic Reports"

    def __str__(self):
        return f"[{self.priority}] {self.issue} at {self.location} ({self.submitted_at.strftime('%Y-%m-%d')})"

    def mark_resolved(self):
        """Mark the report as resolved."""
        self.resolved_at = timezone.now()
        self.save()

    def is_spam(self):
        """Check if report is marked as spam."""
        return self.status == 1

    def needs_review(self):
        """Check if report needs admin review."""
        return self.status == 2


# ============================================================================
# AuditLog — Activity tracking for admin panel and compliance
# ============================================================================
class AuditLog(models.Model):
    """
    Tracks all actions for security, compliance, and debugging.
    """

    ACTION_CHOICES = [
        ("report_created", "Report Submitted"),
        ("report_modified", "Report Modified"),
        ("report_reviewed", "Report Reviewed"),
        ("report_deleted", "Report Deleted"),
        ("spam_flagged", "Spam Flagged"),
        ("upvote_added", "Upvote Added"),
        ("admin_login", "Admin Login"),
        ("admin_action", "Admin Action"),
        ("export_data", "Data Export"),
        ("ai_analysis", "AI Analysis Run"),
    ]

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    report = models.ForeignKey(
        CivicReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    admin_username = models.CharField(max_length=150, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "portal_audit_log"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"]), models.Index(fields=["action"])]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        return f"{self.action} by {self.admin_username or 'system'} at {self.created_at}"


# ============================================================================
# HotspotAnalysis — Geographic clustering for hotspot detection
# ============================================================================
class HotspotAnalysis(models.Model):
    """
    Stores computed hotspot data for geographic analysis.
    Represents clusters of similar issues in specific areas.
    """

    location = models.CharField(max_length=255)
    issue_type = models.CharField(max_length=50)
    report_count = models.IntegerField(default=1)
    avg_risk_score = models.FloatField(default=0)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "portal_hotspot_analysis"
        ordering = ["-report_count"]
        unique_together = ["location", "issue_type"]
        verbose_name = "Hotspot Analysis"
        verbose_name_plural = "Hotspot Analyses"

    def __str__(self):
        return f"{self.issue_type} hotspot at {self.location} ({self.report_count} reports)"


# ============================================================================
# AdminSettings — Configurable system parameters
# ============================================================================
class AdminSettings(models.Model):
    """
    System-wide settings for easy admin panel configuration without code changes.
    """

    key = models.CharField(max_length=100, unique=True, primary_key=True)
    value = models.TextField()
    description = models.CharField(max_length=255, blank=True)
    updated_by = models.CharField(max_length=150, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "portal_admin_settings"
        verbose_name = "Admin Setting"
        verbose_name_plural = "Admin Settings"

    def __str__(self):
        return f"{self.key} = {self.value[:50]}"
