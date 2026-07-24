"""
JanRakshak AI — Portal Views
Bridges Django HTTP layer with the self-contained AI pipeline in services.py.
All AI, database, and security logic is now Django-native (no external files needed).
"""

import json
import logging
import re
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services import (
    Database,
    AIEngine,
    PhotoAnalyzer,
    AIMemory,
    DuplicateDetector,
    HotspotAnalyzer,
    DataProtection,
    EmergencyContacts,
    Assistant,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service singletons — initialized once at module load
# ---------------------------------------------------------------------------
_db = Database()
_db.create_database()

_services = {
    "ai":         AIEngine(),
    "photo_ai":   PhotoAnalyzer(),
    "db":         _db,
    "memory":     AIMemory(),
    "hotspot":    HotspotAnalyzer(),
    "detector":   DuplicateDetector(),
    "protection": DataProtection(),
    "emergency":  EmergencyContacts(),
    "assistant":  Assistant(),
}


# ---------------------------------------------------------------------------
# Helper: build metric context used on both dashboard and home
# ---------------------------------------------------------------------------
def _build_metrics():
    db = _services["db"]
    total = db.get_total_reports()
    avg_risk = db.get_average_risk()
    top_issue = db.get_most_common_issue()

    issue_rows = db.get_reports_by_issue()
    priority_rows = db.get_reports_by_priority()

    return {
        "total_reports": total,
        "avg_risk": avg_risk,
        "top_issue": top_issue[0] if top_issue else "None",
        "issue_distribution": [
            {"label": row[0], "count": row[1]} for row in issue_rows
        ],
        "priority_distribution": [
            {"label": row[0], "count": row[1]} for row in priority_rows
        ],
        "top_locations": db.get_top_locations(),
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def dashboard(request):
    """
    Main analytics dashboard.
    Passes chart-ready JSON blobs to the template for Chart.js consumption.
    """
    metrics = _build_metrics()

    # Serialize distribution data for inline JS consumption
    metrics["issue_distribution_json"] = json.dumps(metrics["issue_distribution"])
    metrics["priority_distribution_json"] = json.dumps(metrics["priority_distribution"])

    return render(request, "portal/dashboard.html", metrics)


def report_issue(request):
    """
    Civic issue reporting form (GET renders form, POST handled via AJAX).
    """
    if request.method == "GET":
        return render(request, "portal/report_issue.html")
    return JsonResponse({"error": "Use POST via AJAX"}, status=405)


@csrf_exempt
@require_http_methods(["POST"])
def analyze_photo(request):
    """AJAX endpoint: analyze uploaded image and generate editable description via Gemini API."""
    try:
        payload = json.loads(request.body)
        photo_data = payload.get("photo_data", "")
        photo_name = payload.get("photo_name", "")
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    if not photo_data:
        return JsonResponse({"error": "Photo data is required"}, status=400)

    try:
        result = _services["photo_ai"].analyze_photo_data(photo_data, photo_name=photo_name)
        return JsonResponse({
            "success": True,
            "analysis": result,
            "auto_description": result.get("Auto Description", ""),
        })
    except Exception as exc:
        logger.warning("Image analysis error: %s", exc)
        exc_str = str(exc)
        is_quota = "429" in exc_str or "quota" in exc_str.lower() or "rate" in exc_str.lower()
        retry_match = re.search(r"Please retry in ([\d.]+s)", exc_str)
        retry_in = retry_match.group(1) if retry_match else None
        if is_quota:
            retry_hint = f" Please retry in {retry_in}." if retry_in else ""
            user_message = (
                f"AI photo analysis is temporarily unavailable \u2014 API quota limit reached.{retry_hint} "
                "Or please describe the issue manually in the field above."
            )
        else:
            user_message = f"AI photo analysis failed: {exc_str}"
        error_response = {
            "success": False,
            "error": user_message,
            "ai_quota_error": is_quota,
        }
        if retry_in:
            error_response["retry_in"] = retry_in
        return JsonResponse(error_response, status=400)


def _reconcile_analysis(description: str, photo_ai_analysis: dict = None) -> dict:
    """Reconciles text description analysis with photo AI classification results.

    Raises on any AI failure — callers must catch and return a proper error response.
    No silent guessing or preset fallbacks are used.
    """
    ai_engine = _services["ai"]

    # If a valid, non-error photo AI result is available, prefer it
    if (
        photo_ai_analysis
        and isinstance(photo_ai_analysis, dict)
        and photo_ai_analysis.get("Issue")
        and not photo_ai_analysis.get("ai_quota_error")
    ):
        return {
            "Issue": photo_ai_analysis["Issue"],
            "Priority": photo_ai_analysis["Priority"],
            "Department": photo_ai_analysis["Department"],
            "Confidence": photo_ai_analysis["Confidence"],
            "Risk Score": photo_ai_analysis["Risk Score"],
            "Reason": photo_ai_analysis["Reason"],
            "Suggested Action": photo_ai_analysis["Suggested Action"],
            "Advice": photo_ai_analysis["Advice"],
        }

    # Fall through to text-based Gemini AI — raises on failure, no keyword guessing
    if not description:
        raise ValueError(
            "A description or valid photo analysis is required to classify this report. "
            "AI photo analysis may have failed — please describe the issue manually."
        )
    return ai_engine.analyze(description)


@csrf_exempt
@require_http_methods(["POST"])
def preview_analysis(request):
    """
    AJAX endpoint: runs the AI classification & hotspot analysis without saving to DB,
    returning JSON so client can render the verification popup modal.
    """
    try:
        payload = json.loads(request.body)
        description = (payload.get("description") or "").strip()
        location = (payload.get("location") or "").strip()
        photo_ai_analysis = payload.get("photo_ai_analysis")
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    if not location:
        return JsonResponse({"error": "Location is required before submitting a report."}, status=400)

    if not description and not photo_ai_analysis:
        return JsonResponse({"error": "Description or photo analysis is required"}, status=400)

    if not description and photo_ai_analysis:
        description = photo_ai_analysis.get(
            "Auto Description",
            "AI detected a civic issue from uploaded photo.",
        )

    db         = _services["db"]
    detector   = _services["detector"]
    protection = _services["protection"]
    hotspot    = _services["hotspot"]

    duplicate = detector.find_duplicate(description, location, db.get_reports())
    
    try:
        result = _reconcile_analysis(description, photo_ai_analysis)
    except Exception as exc:
        return JsonResponse({"error": f"Gemini AI Analysis Error: {str(exc)}"}, status=400)

    secure_report = protection.anonymize_report(description, location)
    hotspot_data = hotspot.analyze(secure_report["location"])

    return JsonResponse({
        "success": True,
        "duplicate": duplicate,
        "analysis": result,
        "hotspot": hotspot_data,
        "privacy_hash": secure_report["fingerprint"][:12],
        "sanitized_location": secure_report["location"],
    })


@csrf_exempt
@require_http_methods(["POST"])
def submit_report(request):
    """
    AJAX endpoint: receives JSON with description + location + user verification feedback,
    runs the full AI pipeline, updates routing if user corrected department, saves to SQLite.
    """
    try:
        payload = json.loads(request.body)
        description = (payload.get("description") or "").strip()
        location = (payload.get("location") or "").strip()
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        photo_ai_analysis = payload.get("photo_ai_analysis")
        ai_correct = payload.get("ai_correct", True)
        corrected_department = (payload.get("corrected_department") or "").strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    if not location:
        return JsonResponse({"error": "Location is required before submitting a report."}, status=400)

    if not description and not photo_ai_analysis:
        return JsonResponse({"error": "Description or photo analysis is required"}, status=400)

    if not description and photo_ai_analysis:
        description = photo_ai_analysis.get(
            "Auto Description",
            "AI detected a civic issue from uploaded photo.",
        )

    db         = _services["db"]
    detector   = _services["detector"]
    protection = _services["protection"]
    memory     = _services["memory"]
    hotspot    = _services["hotspot"]

    # --- Duplicate detection ---
    duplicate = detector.find_duplicate(description, location, db.get_reports())

    # --- Auto upvote for duplicate reports (do not create new duplicate row) ---
    if duplicate.get("duplicate") and duplicate.get("report_id"):
        upvote_result = db.upvote_report(int(duplicate["report_id"]))
        if upvote_result:
            protection.audit_log(
                "REPORT_AUTO_UPVOTED",
                {
                    "report_id": upvote_result["id"],
                    "upvotes": upvote_result["upvotes"],
                    "similarity": duplicate.get("similarity", 0),
                },
            )
            return JsonResponse({
                "success": True,
                "auto_upvoted": True,
                "duplicate": duplicate,
                "report_id": upvote_result["id"],
                "upvotes": upvote_result["upvotes"],
                "message": f"Duplicate detected. Existing Report #{upvote_result['id']} upvoted.",
                "latitude": latitude,
                "longitude": longitude,
            })

    # --- AI classification ---
    result = _reconcile_analysis(description, photo_ai_analysis)

    # Incorporate citizen verification feedback
    result["ai_correct"] = bool(ai_correct)
    if not ai_correct and corrected_department:
        result["Department"] = corrected_department
        result["Reason"] += f" (User specified routing: {corrected_department})"

    memory_data = memory.remember(result)

    # --- Privacy sanitization ---
    secure_report = protection.anonymize_report(description, location)

    # --- Persist ---
    photo_data = payload.get("photo_data")
    db.save_report(
        secure_report["description"],
        secure_report["location"],
        result,
        photo_path=photo_data,
    )
    protection.audit_log(
        "django_report_saved",
        {
            "issue":       result["Issue"],
            "priority":    result["Priority"],
            "ai_correct":  ai_correct,
            "department":  result["Department"],
            "fingerprint": secure_report["fingerprint"],
        },
    )

    # --- Hotspot analysis ---
    hotspot_data = hotspot.analyze(secure_report["location"])

    return JsonResponse({
        "success": True,
        "duplicate": duplicate,
        "analysis": result,
        "memory": memory_data,
        "hotspot": hotspot_data,
        "privacy_hash": secure_report["fingerprint"][:12],
        "sanitized_location": secure_report["location"],
        "latitude": latitude,
        "longitude": longitude,
    })


def view_reports(request):
    """
    Paginated list of all saved reports.
    Supports keyword search via GET param ?q=<keyword>.
    """
    keyword = request.GET.get("q", "").strip()
    db = _services["db"]

    if keyword:
        raw_reports = db.search_reports(keyword)
    else:
        raw_reports = db.get_reports()

    # Map tuple positions to named keys
    columns = [
        "id", "description", "location", "issue", "priority",
        "department", "confidence", "advice", "risk_score",
        "reason", "suggested_action", "submitted_at", "photo_path", "is_spam", "upvotes"
    ]
    
    reports = []
    import datetime
    for row in raw_reports:
        r = dict(zip(columns, row))
        if r.get("submitted_at"):
            try:
                # SQLite CURRENT_TIMESTAMP is in format "YYYY-MM-DD HH:MM:SS"
                r["submitted_at"] = datetime.datetime.strptime(r["submitted_at"], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        reports.append(r)

    return render(request, "portal/view_reports.html", {
        "reports": reports,
        "keyword": keyword,
    })


@csrf_exempt
@require_http_methods(["POST"])
def upvote_report(request):
    """
    AJAX endpoint: Upvote an existing report when a duplicate issue is detected.
    """
    try:
        payload = json.loads(request.body)
        report_id = int(payload.get("report_id"))
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return JsonResponse({"error": "Invalid report_id"}, status=400)

    db = _services["db"]
    protection = _services["protection"]

    res = db.upvote_report(report_id)
    if not res:
        return JsonResponse({"error": "Report not found"}, status=404)

    protection.audit_log("REPORT_UPVOTED", {"report_id": report_id, "upvotes": res["upvotes"]})

    return JsonResponse({
        "success": True,
        "report_id": report_id,
        "upvotes": res["upvotes"],
        "message": f"Successfully upvoted Report #{report_id}.",
    })


@csrf_exempt
@require_http_methods(["POST"])
def toggle_spam(request, report_id):
    """AJAX endpoint: resolve a report's spam status (0 for active, 1 for spam, or toggles)."""
    db = _services["db"]
    status_val = None
    try:
        if request.body:
            payload = json.loads(request.body)
            action = payload.get("action")
            if action == "active":
                status_val = 0
            elif action == "spam":
                status_val = 1
    except Exception:
        pass

    if status_val is not None:
        new_status = db.set_spam_status(report_id, status_val)
    else:
        new_status = db.toggle_spam(report_id)
        
    if new_status is None:
        return JsonResponse({"error": "Report not found"}, status=404)
    return JsonResponse({"success": True, "is_spam": new_status})


def emergency(request):
    """Emergency contacts directory with optional search."""
    keyword = request.GET.get("q", "").strip()
    em = _services["emergency"]

    if keyword:
        contacts = list(em.search_contact(keyword))
    else:
        contacts = list(em.contacts.items())

    contact_list = [
        {
            "department":  dept,
            "phone":       info["number"],
            "description": info["description"],
        }
        for dept, info in contacts
    ]

    return render(request, "portal/emergency.html", {
        "contacts": contact_list,
        "keyword": keyword,
    })


@csrf_exempt
@require_http_methods(["POST"])
def ask_assistant(request):
    """AJAX: Answer an assistant question about civic issues."""
    try:
        payload = json.loads(request.body)
        question = payload.get("question", "").strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"error": "Invalid request"}, status=400)

    if not question:
        return JsonResponse({"error": "Question is required"}, status=400)

    response = _services["assistant"].ask(question)
    return JsonResponse(response)
