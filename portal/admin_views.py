"""
JanRakshak AI — Admin Panel Views
Session-based authentication with full report management capabilities.
"""

import json
import csv
import datetime
import logging
from functools import wraps

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .services import Database

logger = logging.getLogger(__name__)

_db = Database()


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------

def admin_required(view_fn):
    """
    Redirect to login for page views; return JSON 401 for AJAX/API calls
    if the admin session is not present.
    """
    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("admin_logged_in"):
            if (request.headers.get("X-Requested-With") == "XMLHttpRequest"
                    or "json" in request.headers.get("Content-Type", "")
                    or request.path.startswith("/admin-panel/api/")):
                return JsonResponse({"error": "Authentication required"}, status=401)
            return redirect("admin_panel:login")
        return view_fn(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _map_reports(raw_rows):
    """Convert DB tuples → list of dicts."""
    columns = [
        "id", "description", "location", "issue", "priority",
        "department", "confidence", "advice", "risk_score",
        "reason", "suggested_action", "submitted_at", "photo_path", "is_spam", "upvotes",
    ]
    reports = []
    for row in raw_rows:
        r = dict(zip(columns, row))
        if r.get("submitted_at") and isinstance(r["submitted_at"], str):
            try:
                r["submitted_at"] = datetime.datetime.strptime(r["submitted_at"], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        reports.append(r)
    return reports


def _get_stats(db):
    """Return a stats dict for the dashboard using Django ORM."""
    from portal.models import CivicReport
    from django.db.models import Count, Avg
    from django.utils import timezone
    from django.db.models.functions import TruncDate

    total = CivicReport.objects.count()
    active = CivicReport.objects.filter(status=0).count()
    spam_count = CivicReport.objects.filter(status=1).count()
    review_count = CivicReport.objects.filter(status=2).count()
    avg_risk = round(CivicReport.objects.aggregate(avg=Avg("risk_score"))["avg"] or 0, 1)

    priority_rows = (CivicReport.objects
                     .filter(status=0)
                     .values("priority")
                     .annotate(cnt=Count("priority")))
    priority_counts = {r["priority"]: r["cnt"] for r in priority_rows}

    issue_rows = (CivicReport.objects
                  .filter(status=0)
                  .values("issue")
                  .annotate(cnt=Count("issue"))
                  .order_by("-cnt")[:8])
    issue_data = [{"label": r["issue"], "count": r["cnt"]} for r in issue_rows]

    dept_rows = (CivicReport.objects
                 .filter(status=0)
                 .values("department")
                 .annotate(cnt=Count("department"))
                 .order_by("-cnt")[:6])
    dept_data = [{"label": r["department"], "count": r["cnt"]} for r in dept_rows]

    risk_low = CivicReport.objects.filter(status=0, risk_score__lt=30).count()
    risk_med = CivicReport.objects.filter(status=0, risk_score__gte=30, risk_score__lt=60).count()
    risk_high = CivicReport.objects.filter(status=0, risk_score__gte=60, risk_score__lt=80).count()
    risk_crit = CivicReport.objects.filter(status=0, risk_score__gte=80).count()

    seven_days_ago = timezone.now() - datetime.timedelta(days=7)
    recent_rows = (CivicReport.objects
                   .filter(submitted_at__gte=seven_days_ago)
                   .annotate(day=TruncDate("submitted_at"))
                   .values("day")
                   .annotate(cnt=Count("id"))
                   .order_by("day"))
    recent_data = [{"day": str(r["day"]), "count": r["cnt"]} for r in recent_rows]

    loc_rows = (CivicReport.objects
                .filter(status=0)
                .exclude(location="Unknown")
                .values("location")
                .annotate(cnt=Count("location"))
                .order_by("-cnt")[:5])
    top_locations = [{"location": r["location"], "count": r["cnt"]} for r in loc_rows]

    return {
        "total": total,
        "active": active,
        "spam": spam_count,
        "review": review_count,
        "avg_risk": avg_risk,
        "priority_counts": priority_counts,
        "issue_data": issue_data,
        "issue_data_json": json.dumps(issue_data),
        "dept_data": dept_data,
        "dept_data_json": json.dumps(dept_data),
        "risk_buckets": [risk_low, risk_med, risk_high, risk_crit],
        "risk_buckets_json": json.dumps([risk_low, risk_med, risk_high, risk_crit]),
        "recent_data": recent_data,
        "recent_data_json": json.dumps(recent_data),
        "top_locations": top_locations,
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def admin_login(request):
    """Admin login page."""
    if request.session.get("admin_logged_in"):
        return redirect("admin_panel:dashboard")

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        if (username == settings.ADMIN_PANEL_USERNAME
                and password == settings.ADMIN_PANEL_PASSWORD):
            request.session["admin_logged_in"] = True
            request.session["admin_username"] = username
            return redirect("admin_panel:dashboard")
        error = "Invalid username or password."

    return render(request, "admin_panel/login.html", {"error": error})


def admin_logout(request):
    """Clear admin session."""
    request.session.flush()
    return redirect("admin_panel:login")


@admin_required
def admin_dashboard(request):
    """Main analytics dashboard."""
    stats = _get_stats(_db)
    risk_rows = [
        ("Low (0–29)",       "#10B981", 0),
        ("Medium (30–59)",   "#F59E0B", 1),
        ("High (60–79)",     "#F97316", 2),
        ("Critical (80+)",   "#EF4444", 3),
    ]
    return render(request, "admin_panel/dashboard.html", {
        "stats": stats,
        "risk_rows": risk_rows,
        "admin_username": request.session.get("admin_username", "Admin"),
        "active_page": "dashboard",
    })


@admin_required
def admin_reports(request):
    """Report management with filters."""
    from portal.models import CivicReport
    from django.db.models import Count

    keyword = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "all")

    if keyword:
        raw = _db.search_reports(keyword)
    else:
        raw = _db.get_reports()

    reports = _map_reports(raw)

    status_map = {"active": 0, "spam": 1, "review": 2}
    if status_filter in status_map:
        reports = [r for r in reports if r["is_spam"] == status_map[status_filter]]

    counts = {
        "all": CivicReport.objects.count(),
        "active": CivicReport.objects.filter(status=0).count(),
        "spam": CivicReport.objects.filter(status=1).count(),
        "review": CivicReport.objects.filter(status=2).count(),
    }

    tabs = [
        ("all",    "All Reports",   "all"),
        ("active", "Active",        "active"),
        ("review", "Needs Review",  "review"),
        ("spam",   "Spam",          "spam"),
    ]
    return render(request, "admin_panel/reports.html", {
        "reports": reports,
        "keyword": keyword,
        "status_filter": status_filter,
        "counts": counts,
        "tabs": tabs,
        "admin_username": request.session.get("admin_username", "Admin"),
        "active_page": "reports",
    })


@admin_required
def admin_analytics(request):
    """Analytics deep-dive page."""
    stats = _get_stats(_db)
    return render(request, "admin_panel/analytics.html", {
        "stats": stats,
        "admin_username": request.session.get("admin_username", "Admin"),
        "active_page": "analytics",
    })


@admin_required
def admin_audit_log(request):
    """View the audit log file."""
    from .services import AUDIT_LOG_PATH
    lines = []
    try:
        with open(AUDIT_LOG_PATH, "r") as f:
            lines = f.readlines()[-200:]
        lines = [l.rstrip() for l in reversed(lines)]
    except FileNotFoundError:
        lines = ["No audit log found."]

    return render(request, "admin_panel/audit_log.html", {
        "log_lines": lines,
        "admin_username": request.session.get("admin_username", "Admin"),
        "active_page": "audit_log",
    })


@admin_required
def admin_settings(request):
    """Settings overview page."""
    return render(request, "admin_panel/settings.html", {
        "admin_username": request.session.get("admin_username", "Admin"),
        "active_page": "settings",
        "settings": {
            "GEMINI_API_KEY": ("*" * 8 + settings.GEMINI_API_KEY[-6:]) if getattr(settings, "GEMINI_API_KEY", "") else "Not Set",
            "TIME_ZONE": settings.TIME_ZONE,
            "DEBUG": settings.DEBUG,
            "ADMIN_USERNAME": settings.ADMIN_PANEL_USERNAME,
        },
    })


# ---------------------------------------------------------------------------
# API endpoints for admin actions
# ---------------------------------------------------------------------------

@admin_required
@require_http_methods(["POST"])
def api_resolve_report(request, report_id):
    """Set report status: 0=active, 1=spam, 2=needs_review."""
    try:
        payload = json.loads(request.body)
        action = payload.get("action")
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    status_map = {"active": 0, "spam": 1, "review": 2}
    if action not in status_map:
        return JsonResponse({"error": "Invalid action"}, status=400)

    new_status = _db.set_spam_status(report_id, status_map[action])
    if new_status is None:
        return JsonResponse({"error": "Report not found"}, status=404)

    return JsonResponse({"success": True, "is_spam": new_status, "action": action})


@admin_required
@require_http_methods(["POST"])
def api_delete_report(request, report_id):
    """Permanently delete a report."""
    from portal.models import CivicReport
    try:
        report = CivicReport.objects.get(id=report_id)
        report.delete()
        return JsonResponse({"success": True})
    except CivicReport.DoesNotExist:
        return JsonResponse({"error": "Report not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@admin_required
def api_export_csv(request):
    """Export all reports as a CSV download."""
    raw = _db.get_reports()
    reports = _map_reports(raw)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="janrakshak_reports.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID", "Description", "Location", "Issue", "Priority",
        "Department", "Confidence", "Risk Score", "Reason",
        "Suggested Action", "Status", "Submitted At",
    ])
    status_labels = {0: "Active", 1: "Spam", 2: "Needs Review"}
    for r in reports:
        writer.writerow([
            r["id"], r["description"], r["location"], r["issue"],
            r["priority"], r["department"], r["confidence"], r["risk_score"],
            r["reason"], r["suggested_action"],
            status_labels.get(r["is_spam"], "Unknown"),
            r["submitted_at"],
        ])
    return response


@admin_required
def api_report_detail(request, report_id):
    """Return full report detail as JSON for modal display."""
    from portal.models import CivicReport
    try:
        report = CivicReport.objects.get(id=report_id)
        status_labels = {0: "Active", 1: "Spam", 2: "Needs Review"}
        data = {
            "id": report.id,
            "description": report.description,
            "location": report.location,
            "issue": report.issue,
            "priority": report.priority,
            "department": report.department,
            "confidence": report.confidence,
            "advice": report.advice,
            "risk_score": report.risk_score,
            "reason": report.reason,
            "suggested_action": report.suggested_action,
            "submitted_at": report.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if report.submitted_at else "",
            "photo_path": report.photo.url if report.photo else None,
            "is_spam": report.status,
            "status_label": status_labels.get(report.status, "Unknown"),
        }
        return JsonResponse({"success": True, "report": data})
    except CivicReport.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

