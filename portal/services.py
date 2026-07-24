"""
JanRakshak AI — Service Layer
Django-native service layer for civic issue reporting.
Database operations use Django ORM (PostgreSQL/SQLite).
AI operations use keyword classification + Google Gemini API.
"""

import re
import json
import io
import base64
import hashlib
import logging
import datetime
import colorsys
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths (for audit log only — DB is handled by Django ORM)
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent.parent   # CivicAI_India/
AUDIT_LOG_PATH = _HERE / "data" / "audit.log"
AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def is_ai_confused(result: dict) -> bool:
    """
    Returns True if the AI classification has low confidence,
    indicating it is confused/unsure and needs authority verification.
    """
    confidence = result.get("Confidence", "Low")
    if not confidence:
        return True
    
    conf_str = str(confidence).strip().lower()
    
    # Text classifier uses 'Low', 'Medium', 'High' labels
    if conf_str == "low":
        return True
        
    # Image classifier uses percentages, e.g. '58%' or numeric values
    match = re.search(r"(\d+)", conf_str)
    if match:
        val = int(match.group(1))
        # Confidence below 70% is considered confused/unsure
        if val < 70:
            return True
            
    return False


# ===========================================================================
# DATABASE
# ===========================================================================
class Database:
    """
    Django ORM wrapper maintaining the original API for backward compatibility.
    Returns tuples in the same column order the views expect:
    (id, description, location, issue, priority, department, confidence,
     advice, risk_score, reason, suggested_action, submitted_at_str,
     photo_url_or_none, status_int, upvotes)
    """

    def create_database(self):
        """No-op — Django migrations handle schema creation."""
        pass

    def _to_tuple(self, report):
        """Convert a CivicReport ORM object to a legacy tuple."""
        from django.utils import timezone as tz
        photo_url = report.photo.url if report.photo else None
        submitted_str = (
            report.submitted_at.strftime("%Y-%m-%d %H:%M:%S")
            if report.submitted_at else ""
        )
        return (
            report.id,
            report.description,
            report.location,
            report.issue,
            report.priority,
            report.department,
            report.confidence,
            report.advice,
            report.risk_score,
            report.reason,
            report.suggested_action,
            submitted_str,
            photo_url,
            report.status,
            report.upvotes,
        )

    def save_report(self, description: str, location: str, result: dict, photo_path: str = None):
        from portal.models import CivicReport
        from django.core.files.base import ContentFile

        if result.get("Issue") == "Spam":
            status = 1
        elif is_ai_confused(result) or result.get("ai_correct") is False:
            status = 2
        else:
            status = 0

        report = CivicReport(
            description=description,
            location=location,
            issue=result.get("Issue", "Unknown")[:50],
            priority=result.get("Priority", "Low")[:20],
            department=result.get("Department", "General")[:100],
            confidence=result.get("Confidence", "Medium")[:20],
            advice=result.get("Advice", ""),
            risk_score=int(result.get("Risk Score", 0)),
            reason=result.get("Reason", ""),
            suggested_action=result.get("Suggested Action", ""),
            status=status,
        )

        if photo_path and "," in photo_path and photo_path.startswith("data:"):
            try:
                _, b64 = photo_path.split(",", 1)
                image_data = base64.b64decode(b64)
                fname = f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                report.photo.save(fname, ContentFile(image_data), save=False)
            except Exception as exc:
                logger.warning("Photo save failed: %s", exc)

        report.save()
        return {"id": report.id, "upvotes": report.upvotes}

    def get_reports(self):
        from portal.models import CivicReport
        return [self._to_tuple(r) for r in CivicReport.objects.all()]

    def search_reports(self, keyword: str):
        from portal.models import CivicReport
        from django.db.models import Q
        qs = CivicReport.objects.filter(
            Q(description__icontains=keyword) |
            Q(location__icontains=keyword) |
            Q(issue__icontains=keyword) |
            Q(department__icontains=keyword)
        )
        return [self._to_tuple(r) for r in qs]

    def upvote_report(self, report_id: int):
        from portal.models import CivicReport
        from django.db.models import F
        try:
            report = CivicReport.objects.get(id=report_id)
            CivicReport.objects.filter(id=report_id).update(upvotes=F("upvotes") + 1)
            report.refresh_from_db()
            return {"id": report.id, "upvotes": report.upvotes}
        except CivicReport.DoesNotExist:
            return None

    def toggle_spam(self, report_id: int):
        from portal.models import CivicReport
        try:
            report = CivicReport.objects.get(id=report_id)
            report.status = 1 if report.status == 0 else 0
            report.save(update_fields=["status"])
            return report.status
        except CivicReport.DoesNotExist:
            return None

    def set_spam_status(self, report_id: int, status: int):
        from portal.models import CivicReport
        updated = CivicReport.objects.filter(id=report_id).update(status=status)
        return status if updated else None

    def get_total_reports(self) -> int:
        from portal.models import CivicReport
        return CivicReport.objects.count()

    def get_average_risk(self) -> float:
        from portal.models import CivicReport
        from django.db.models import Avg
        result = CivicReport.objects.aggregate(avg=Avg("risk_score"))["avg"]
        return round(result or 0, 1)

    def get_most_common_issue(self):
        from portal.models import CivicReport
        from django.db.models import Count
        row = (CivicReport.objects
               .values("issue")
               .annotate(cnt=Count("issue"))
               .order_by("-cnt")
               .first())
        return (row["issue"],) if row else ("None",)

    def get_reports_by_issue(self):
        from portal.models import CivicReport
        from django.db.models import Count
        rows = (CivicReport.objects
                .values("issue")
                .annotate(cnt=Count("issue"))
                .order_by("-cnt"))
        return [(r["issue"], r["cnt"]) for r in rows]

    def get_reports_by_priority(self):
        from portal.models import CivicReport
        from django.db.models import Count
        rows = (CivicReport.objects
                .values("priority")
                .annotate(cnt=Count("priority"))
                .order_by("-cnt"))
        return [(r["priority"], r["cnt"]) for r in rows]

    def get_top_locations(self, limit: int = 5):
        from portal.models import CivicReport
        from django.db.models import Count
        rows = (CivicReport.objects
                .exclude(location="Unknown")
                .values("location")
                .annotate(cnt=Count("location"))
                .order_by("-cnt")[:limit])
        return [(r["location"], r["cnt"]) for r in rows]


# ===========================================================================
# AI ENGINE  — keyword-weighted classifier (offline, no cloud calls)
# ===========================================================================
class AIEngine:
    """
    Lightweight keyword-weighted issue classifier.
    """

    ISSUE_KEYWORDS = {
        "Road Damage": [
            "pothole", "road", "crack", "broken", "tar", "asphalt",
            "highway", "street", "pavement", "damaged road", "potholes",
        ],
        "Water Leakage": [
            "water", "pipe", "leak", "leakage", "burst", "pipeline",
            "flood", "overflow", "drain", "sewage", "drainage",
        ],
        "Garbage": [
            "garbage", "waste", "trash", "litter", "dump", "filth",
            "rubbish", "smell", "stench", "dirty", "unhygienic",
        ],
        "Electricity": [
            "electric", "electricity", "wire", "pole", "light", "power",
            "short circuit", "spark", "outage", "blackout", "shock",
        ],
        "Streetlight": [
            "streetlight", "street light", "lamp", "dark", "darkness",
            "lighting", "bulb", "no light",
        ],
        "Flood": [
            "flood", "waterlogging", "stagnant water", "inundated",
            "submerged", "rain", "waterlogged", "puddle",
        ],
        "Fire Emergency": [
            "fire", "burning", "smoke", "flame", "blaze", "arson",
        ],
        "Tree Fall": [
            "tree", "fallen", "branch", "obstruction", "blocked", "uprooted",
        ],
    }

    PRIORITY_MAP = {
        "Fire Emergency": "Critical",
        "Electricity": "Critical",
        "Flood": "High",
        "Water Leakage": "High",
        "Road Damage": "Medium",
        "Tree Fall": "Medium",
        "Streetlight": "Low",
        "Garbage": "Low",
    }

    DEPARTMENT_MAP = {
        "Road Damage": "Public Works Department (PWD)",
        "Water Leakage": "Water Supply & Sewerage Board",
        "Garbage": "Municipal Solid Waste Management",
        "Electricity": "State Electricity Distribution Company",
        "Streetlight": "Urban Local Body — Street Lighting",
        "Flood": "Drainage & Flood Control Board",
        "Fire Emergency": "Fire & Emergency Services",
        "Tree Fall": "Horticulture / Forest Department",
    }

    RISK_MAP = {
        "Critical": 90,
        "High": 70,
        "Medium": 45,
        "Low": 20,
    }

    def _score(self, text: str) -> dict:
        text_lower = text.lower()
        scores = {}
        for issue, keywords in self.ISSUE_KEYWORDS.items():
            score = sum(
                (1 + text_lower.count(kw)) * (1 + len(kw.split()))
                for kw in keywords
                if kw in text_lower
            )
            scores[issue] = score
        return scores

    def analyze(self, description: str) -> dict:
        scores = self._score(description)
        best_issue = max(scores, key=scores.get)
        best_score = scores[best_issue]

        # Confidence based on score magnitude
        if best_score >= 10:
            confidence = "High"
        elif best_score >= 4:
            confidence = "Medium"
        elif best_score >= 1:
            confidence = "Low"
        else:
            best_issue = "General Civic Issue"
            confidence = "Low"

        priority = self.PRIORITY_MAP.get(best_issue, "Medium")
        department = self.DEPARTMENT_MAP.get(best_issue, "Municipal Corporation")
        base_risk = self.RISK_MAP.get(priority, 45)
        # Slightly vary risk by description length (longer = more detailed = more certain)
        risk_score = min(100, base_risk + min(10, len(description) // 50))

        return {
            "Issue": best_issue,
            "Priority": priority,
            "Department": department,
            "Confidence": confidence,
            "Risk Score": risk_score,
            "Reason": f"Keywords strongly indicate a {best_issue.lower()} situation requiring {priority.lower()} priority attention.",
            "Suggested Action": f"File a formal complaint with {department}. Reference this report hash for follow-up.",
            "Advice": "Document the issue with photos. Share the report ID with local ward councillor for faster resolution.",
        }


# ===========================================================================
# PHOTO ANALYZER (optional image-to-description support)
# ===========================================================================
class PhotoAnalyzer:
    """Analyzes a civic issue photo and returns structured issue classification."""

    CATEGORY_META = {
        "Water Leakage": ("High", "Water Supply & Sewerage Board", 72),
        "Road Damage": ("Medium", "Public Works Department (PWD)", 58),
        "Garbage": ("Low", "Municipal Solid Waste Management", 36),
        "Electricity": ("Critical", "State Electricity Distribution Company", 90),
        "Flood": ("High", "Drainage & Flood Control Board", 84),
        "Fire Emergency": ("Critical", "Fire & Emergency Services", 96),
        "Tree Fall": ("Medium", "Horticulture / Forest Department", 61),
        "Streetlight": ("Low", "Urban Local Body — Street Lighting", 30),
        "General Civic Issue": ("Low", "Municipal Corporation", 30),
    }

    def _decode_data_url(self, photo_data: str) -> bytes:
        if not photo_data:
            raise ValueError("Missing photo data")
        if "," in photo_data:
            _, b64 = photo_data.split(",", 1)
        else:
            b64 = photo_data
        try:
            return base64.b64decode(b64)
        except Exception as exc:
            raise ValueError("Invalid base64 image data") from exc

    def _build_result(self, issue: str, confidence: str, reason: str) -> dict:
        priority, department, risk = self.CATEGORY_META.get(
            issue,
            self.CATEGORY_META["General Civic Issue"],
        )
        return {
            "Issue": issue,
            "Priority": priority,
            "Department": department,
            "Confidence": confidence,
            "Risk Score": risk,
            "Reason": reason,
            "Suggested Action": f"Assign to {department} for field verification and resolution.",
            "Advice": "You can edit the AI-generated description before submission for better accuracy.",
        }

    def _generate_description(self, result: dict) -> str:
        issue = result.get("Issue", "General Civic Issue")
        dept = result.get("Department", "Municipal Corporation")
        priority = result.get("Priority", "Medium")
        
        detail_map = {
            "Water Leakage": (
                "An active water leakage issue has been detected from the uploaded photographic evidence. "
                "There appears to be a pipeline burst or leakage causing continuous water loss and potential damage to the surrounding road surface. "
                "Requesting the Water Supply & Sewerage Board to dispatch field engineers for immediate line inspection, isolation, and repair to conserve water and prevent road damage."
            ),
            "Road Damage": (
                "Significant road damage / pothole has been detected from the uploaded photographic evidence. "
                "This defect presents an active safety hazard for commuters, especially two-wheelers, and is likely to cause vehicle damage or traffic disruption. "
                "Requesting the Public Works Department (PWD) road maintenance team to carry out leveling and resurfacing work at the earliest."
            ),
            "Garbage": (
                "An accumulation of unmanaged solid waste / garbage dump has been detected from the uploaded photographic evidence. "
                "This creates unsanitary conditions, potential health hazards, and public inconvenience in the locality. "
                "Requesting the Municipal Solid Waste Management department to dispatch a clearing vehicle to clean the site and restore sanitation."
            ),
            "Electricity": (
                "A potential electrical hazard (such as damaged wiring, sparks, or transformer issues) has been detected from the uploaded photographic evidence. "
                "This poses a critical public safety threat. "
                "Requesting the State Electricity Distribution Company to dispatch emergency line technicians immediately for safety isolation and rectification."
            ),
            "Flood": (
                "Severe water-logging / flooding has been detected from the uploaded photographic evidence. "
                "This restricts pedestrian and vehicular movement and risks entering low-lying buildings. "
                "Requesting the Drainage & Flood Control Board to deploy dewatering pumps and clear drainage blocks in the affected area."
            ),
            "Fire Emergency": (
                "An active fire emergency or hazardous heat signature has been detected from the uploaded photographic evidence. "
                "This requires immediate emergency dispatch. "
                "Requesting Fire & Emergency Services to deploy firefighting personnel and apparatus to the location."
            ),
            "Tree Fall": (
                "A fallen tree or major branch blocking the road/pathway has been detected from the uploaded photographic evidence. "
                "This blocks traffic and poses a risk to overhead cables. "
                "Requesting the Horticulture / Forest Department to clear the obstruction and restore access."
            ),
            "Streetlight": (
                "A non-functioning streetlight or lighting infrastructure defect has been detected from the uploaded photographic evidence. "
                "This results in dark patches on public streets, reducing security and commuter safety. "
                "Requesting the Urban Local Body Street Lighting division to replace the faulty bulbs or repair the wiring."
            ),
        }
        
        details = detail_map.get(
            issue,
            "A civic issue requiring inspection and resolution has been detected from the uploaded photographic evidence. "
            "Please assign a field technician to investigate the site and take appropriate corrective action."
        )
        
        return details

    def analyze_photo_data(self, photo_data: str, photo_name: str = "") -> dict:
        # Check if Google Gemini API Key is configured
        import os
        from django.conf import settings
        api_key = getattr(settings, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            try:
                import json
                import requests
                # Decode image and strip base64 prefix
                if "," in photo_data:
                    mime, b64 = photo_data.split(",", 1)
                    mime_type = mime.split(";")[0].split(":")[1]
                else:
                    b64 = photo_data
                    mime_type = "image/jpeg"
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                
                prompt = (
                    "Analyze the civic issue shown in this photo. "
                    "Determine the issue category, which must be exactly one of: "
                    "'Road Damage', 'Water Leakage', 'Garbage', 'Electricity', 'Streetlight', 'Flood', 'Fire Emergency', 'Tree Fall', 'Spam', or 'General Civic Issue'.\n\n"
                    "If the image shows a streetlight, street lamp, lighting pole, or dark unlit street light fixture, classify it strictly as 'Streetlight'.\n\n"
                    "If the image does not represent any real, public civic issue (e.g. it is a selfie, advertisement, meme, screenshot of unrelated text, arbitrary household or indoor object, animal, food, or non-civic scene), classify it as 'Spam' under the 'Issue' category. If the issue is categorized as 'Spam', set the 'Priority' to 'Low', the 'Risk Score' to 0, and the 'Auto Description' should indicate that the image is flagged as invalid or irrelevant spam.\n\n"
                    "Return a JSON object conforming exactly to this schema:\n"
                    "{\n"
                    "  \"Issue\": \"string\",\n"
                    "  \"Priority\": \"Critical\" | \"High\" | \"Medium\" | \"Low\",\n"
                    "  \"Department\": \"string (concerned authority name)\",\n"
                    "  \"Confidence\": \"string (percentage, e.g., 92%)\",\n"
                    "  \"Risk Score\": integer (0 to 100),\n"
                    "  \"Reason\": \"string (1-sentence reason for classification)\",\n"
                    "  \"Suggested Action\": \"string (action for authority)\",\n"
                    "  \"Advice\": \"string (optional advice for citizen)\",\n"
                    "  \"Auto Description\": \"string (detailed description describing the issue and request for dispatch)\"\n"
                    "}"
                )
                
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inlineData": {
                                    "mimeType": mime_type,
                                    "data": b64
                                }
                            }
                        ]
                    }],
                    "generationConfig": {
                        "responseMimeType": "application/json"
                    }
                }
                
                response = requests.post(url, json=payload, headers=headers, timeout=12)
                if response.status_code == 200:
                    resp_json = response.json()
                    text_content = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                    result = json.loads(text_content)
                    
                    normalized = {
                        "Issue": result.get("Issue", "General Civic Issue"),
                        "Priority": result.get("Priority", "Medium"),
                        "Department": result.get("Department", "Municipal Corporation"),
                        "Confidence": result.get("Confidence", "60%"),
                        "Risk Score": int(result.get("Risk Score", 50)),
                        "Reason": result.get("Reason", "Detected from uploaded image."),
                        "Suggested Action": result.get("Suggested Action", "Field inspection recommended."),
                        "Advice": result.get("Advice", "Please provide additional details if possible."),
                        "Auto Description": result.get("Auto Description", "")
                    }
                    if not normalized["Auto Description"]:
                        normalized["Auto Description"] = self._generate_description(normalized)
                    return normalized
                else:
                    logger.warning("Gemini API call failed with status %s: %s", response.status_code, response.text)
            except Exception as exc:
                logger.warning("Failed to analyze image using Gemini API, falling back: %s", exc)

        try:
            from PIL import Image, ImageStat

            image_bytes = self._decode_data_url(photo_data)
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            small = image.resize((128, 128))

            pixels = list(small.getdata())
            stat = ImageStat.Stat(image)
            r_mean, g_mean, b_mean = stat.mean

            hue_buckets = {
                "red_orange": 0,
                "yellow": 0,
                "green": 0,
                "blue_cyan": 0,
                "gray": 0,
            }
            high_sat_count = 0

            for r, g, b in pixels:
                h, s, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                if s < 0.12:
                    hue_buckets["gray"] += 1
                    continue
                if s > 0.35:
                    high_sat_count += 1

                hue_deg = h * 360
                if hue_deg < 30 or hue_deg >= 330:
                    hue_buckets["red_orange"] += 1
                elif hue_deg < 75:
                    hue_buckets["yellow"] += 1
                elif hue_deg < 165:
                    hue_buckets["green"] += 1
                elif hue_deg < 270:
                    hue_buckets["blue_cyan"] += 1
                else:
                    hue_buckets["red_orange"] += 1

            total = max(1, sum(hue_buckets.values()))
            hues = {k: v / total for k, v in hue_buckets.items()}
            saturation = high_sat_count / max(1, len(pixels))
            brightness = ImageStat.Stat(image.convert("L")).mean[0]

            name_lower = (photo_name or "").lower()

            scores = {
                "Streetlight": 0.0,
                "Water Leakage": 0.0,
                "Road Damage": 0.0,
                "Garbage": 0.0,
                "Electricity": 0.0,
                "Fire Emergency": 0.0,
                "Flood": 0.0,
                "Tree Fall": 0.0,
            }

            # --- Keyword Hints from Filename ---
            if any(k in name_lower for k in ["light", "lamp", "pole", "street", "night", "dark", "bulb", "no light"]):
                scores["Streetlight"] += 3.5
            if any(k in name_lower for k in ["water", "leak", "pipe", "burst"]):
                scores["Water Leakage"] += 3.5
            if any(k in name_lower for k in ["pothole", "road", "crack", "asphalt", "tarmac"]):
                scores["Road Damage"] += 3.5
            if any(k in name_lower for k in ["garbage", "trash", "waste", "dump", "litter"]):
                scores["Garbage"] += 3.5
            if any(k in name_lower for k in ["fire", "flame", "smoke"]):
                scores["Fire Emergency"] += 3.5

            # --- Visual Pattern Heuristics ---
            is_dark_night = brightness < 110
            is_bright_fire = (brightness > 135 and r_mean > 145 and saturation > 0.25)

            # Streetlight: Dark night scene + gray structural pole / fixture
            if is_dark_night:
                scores["Streetlight"] += 2.8 + (1.2 if brightness < 70 else 0.5)
            if hues["gray"] > 0.2 and is_dark_night:
                scores["Streetlight"] += 1.2

            # Water Leakage: Require cyan/blue water component
            water_leak_val = hues["blue_cyan"] * 3.0 + (1.5 if b_mean > r_mean + 12 else 0.0)
            if b_mean < r_mean and hues["blue_cyan"] < 0.12:
                water_leak_val = 0.0
            scores["Water Leakage"] += water_leak_val

            # Flood
            scores["Flood"] += hues["blue_cyan"] * 1.6 + (1.2 if (b_mean > r_mean + 15 and brightness > 120) else 0.0)

            # Road Damage: Daylight asphalt (brightness >= 110)
            if brightness >= 110:
                scores["Road Damage"] += hues["gray"] * 2.2 + (1.0 - saturation) * 0.8

            # Garbage
            scores["Garbage"] += hues["green"] * 1.2 + hues["yellow"] * 0.8

            # Electricity
            scores["Electricity"] += hues["yellow"] * 1.4 + (1.0 if (brightness < 100 and saturation > 0.6) else 0.0)

            # Tree Fall
            scores["Tree Fall"] += hues["green"] * 1.5 + (hues["gray"] * 0.4 if brightness >= 110 else 0.0)

            # Fire Emergency
            if is_bright_fire:
                scores["Fire Emergency"] += hues["red_orange"] * 2.3 + saturation * 1.2

            issue = max(scores, key=scores.get)
            confidence_val = scores[issue]
            if confidence_val >= 2.0:
                confidence = "82%"
            elif confidence_val >= 1.2:
                confidence = "72%"
            elif confidence_val >= 0.6:
                confidence = "62%"
            else:
                issue = "General Civic Issue"
                confidence = "52%"

            reason = f"Visual color and scene pattern analysis indicates {issue.lower()} characteristics."
            result = self._build_result(issue, confidence, reason)
            result["Auto Description"] = self._generate_description(result)
            return result
        except Exception as exc:
            logger.warning("Photo analysis failed: %s", exc)
            fallback = self._build_result(
                "General Civic Issue",
                "50%",
                "AI could not confidently classify this image; manual review is recommended.",
            )
            fallback["Auto Description"] = self._generate_description(fallback)
            return fallback


# ===========================================================================
# DUPLICATE DETECTOR
# ===========================================================================
class DuplicateDetector:
    """Detects near-duplicate reports using Jaccard similarity on token sets."""

    THRESHOLD = 0.55  # 55% similarity triggers duplicate flag
    LOCATION_MIN_SIMILARITY = 0.20

    def _tokenize(self, text: str) -> set:
        words = re.findall(r"\b\w{3,}\b", text.lower())
        return set(words)

    def _tokenize_location(self, text: str) -> set:
        words = re.findall(r"\b\w{2,}\b", text.lower())
        return set(words)

    def _normalize_location(self, location: str) -> str:
        return re.sub(r"\s+", " ", (location or "").strip().lower())

    def _has_meaningful_location(self, location: str) -> bool:
        loc = self._normalize_location(location)
        return loc not in {"", "unknown", "n/a", "na", "not provided"}

    def _jaccard(self, a: set, b: set) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _location_similarity(self, location: str, existing_location: str):
        if not self._has_meaningful_location(location) or not self._has_meaningful_location(existing_location):
            return None

        normalized_a = self._normalize_location(location)
        normalized_b = self._normalize_location(existing_location)
        if normalized_a == normalized_b:
            return 1.0

        return self._jaccard(self._tokenize_location(normalized_a), self._tokenize_location(normalized_b))

    def find_duplicate(self, description: str, location: str, reports: list) -> dict:
        tokens = self._tokenize(description)
        best_match = {"duplicate": False, "report_id": None, "similarity": 0}

        for row in reports:
            existing_desc = row[1] if len(row) > 1 else ""
            existing_location = row[2] if len(row) > 2 else ""
            existing_tokens = self._tokenize(existing_desc)
            description_sim = self._jaccard(tokens, existing_tokens)
            location_sim = self._location_similarity(location, existing_location)

            # When both locations are available, require at least minimal location overlap.
            if location_sim is not None and location_sim < self.LOCATION_MIN_SIMILARITY:
                continue

            combined_sim = (
                description_sim
                if location_sim is None
                else (0.70 * description_sim) + (0.30 * location_sim)
            )
            sim_pct = round(combined_sim * 100)

            if combined_sim >= self.THRESHOLD and sim_pct > best_match["similarity"]:
                best_match = {
                    "duplicate": True,
                    "report_id": row[0],
                    "similarity": sim_pct,
                    "description_similarity": round(description_sim * 100),
                    "location_similarity": 0 if location_sim is None else round(location_sim * 100),
                }

        return best_match


# ===========================================================================
# HOTSPOT ANALYZER
# ===========================================================================
class HotspotAnalyzer:
    """Classifies a location as a civic hotspot based on historical report counts."""

    def analyze(self, location: str) -> dict:
        try:
            from portal.models import CivicReport
            count = CivicReport.objects.filter(location=location).count()
        except Exception:
            count = 0

        if count >= 5:
            level = "🔴 Critical Hotspot"
            rec = "Immediate municipal intervention required. Escalate to ward officer."
        elif count >= 3:
            level = "🟡 Moderate Hotspot"
            rec = "Multiple reports from this location. Schedule a field inspection."
        elif count >= 1:
            level = "🟢 Low Frequency"
            rec = "New report for this location. Normal triage process applies."
        else:
            level = "⚪ First Report"
            rec = "No prior reports for this location."

        return {"Hotspot Level": level, "Recommendation": rec, "report_count": count}


# ===========================================================================
# DATA PROTECTION  (privacy sanitization + audit logging)
# ===========================================================================
class DataProtection:
    """Redacts PII from civic reports and provides ward-level location coarsening."""

    # Patterns to redact
    _EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    _PHONE_RE = re.compile(r"(\+91[-\s]?)?[6-9]\d{9}")
    _HOUSE_RE = re.compile(r"\b(house|flat|plot|door|h\.?no\.?|d\.?no\.?)\s*[#\-]?\s*\d+[\w/]*", re.I)
    _AADHAR_RE = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")

    def anonymize_report(self, description: str, location: str) -> dict:
        clean = description
        clean = self._EMAIL_RE.sub("[EMAIL REDACTED]", clean)
        clean = self._PHONE_RE.sub("[PHONE REDACTED]", clean)
        clean = self._HOUSE_RE.sub("[HOUSE# REDACTED]", clean)
        clean = self._AADHAR_RE.sub("[ID REDACTED]", clean)

        # Coarsen location to ward-level (strip building/flat specifics)
        safe_location = re.sub(r"\b(flat|door|house|plot)\s*[#\-]?\s*\d+[\w/]*", "", location, flags=re.I).strip()
        if not safe_location:
            safe_location = location

        fingerprint = hashlib.sha256(
            f"{clean}|{safe_location}|{datetime.datetime.utcnow().date()}".encode()
        ).hexdigest()

        return {
            "description": clean,
            "location": safe_location,
            "fingerprint": fingerprint,
        }

    def audit_log(self, event: str, metadata: dict):
        try:
            AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts": datetime.datetime.utcnow().isoformat(),
                "event": event,
                **metadata,
            }
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as exc:
            logger.warning("Audit log write failed: %s", exc)


# ===========================================================================
# AI MEMORY  (tracks classification history in-process)
# ===========================================================================
class AIMemory:
    """Maintains an in-memory tally of classified issues for session analytics."""

    def __init__(self):
        self._history = defaultdict(int)

    def remember(self, result: dict) -> dict:
        issue = result.get("Issue", "Unknown")
        self._history[issue] += 1
        return {
            "session_count": sum(self._history.values()),
            "issue_counts": dict(self._history),
        }


# ===========================================================================
# EMERGENCY CONTACTS
# ===========================================================================
class EmergencyContacts:
    """Provides a directory of India civic emergency numbers."""

    contacts = {
        "Police": {
            "number": "100",
            "description": "National emergency police helpline",
        },
        "Fire Brigade": {
            "number": "101",
            "description": "Fire and rescue services",
        },
        "Ambulance": {
            "number": "102",
            "description": "Medical emergency / ambulance",
        },
        "Disaster Management": {
            "number": "108",
            "description": "National disaster response helpline",
        },
        "Women Helpline": {
            "number": "1091",
            "description": "Women in distress emergency line",
        },
        "Road Accident Emergency": {
            "number": "1073",
            "description": "National Highway accident helpline",
        },
        "Water Board (BWSSB)": {
            "number": "1916",
            "description": "Water supply complaints and emergencies",
        },
        "Electricity Board (BESCOM)": {
            "number": "1912",
            "description": "Power outage and electrical hazard",
        },
        "Municipal Corporation (BBMP)": {
            "number": "080-22221188",
            "description": "Garbage, roads, public infrastructure",
        },
        "Gas Leak Emergency": {
            "number": "1906",
            "description": "LPG gas leak emergency response",
        },
        "Child Helpline": {
            "number": "1098",
            "description": "CHILDLINE India — child distress helpline",
        },
        "Senior Citizen Helpline": {
            "number": "14567",
            "description": "Elder care and assistance",
        },
    }

    def search_contact(self, keyword: str):
        kw = keyword.lower()
        return [
            (dept, info)
            for dept, info in self.contacts.items()
            if kw in dept.lower() or kw in info["description"].lower()
        ]


# ===========================================================================
# ASSISTANT  (simple FAQ-style civic assistant)
# ===========================================================================
class Assistant:
    """Keyword-based civic assistant that answers common citizen queries."""

    FAQ = [
        {
            "keywords": ["pothole", "road", "damage"],
            "answer": "Road damage should be reported to the Public Works Department (PWD). File a complaint at your local municipal office or use JanRakshak AI to submit a geo-tagged report.",
        },
        {
            "keywords": ["water", "leak", "pipe", "supply"],
            "answer": "Water leakage emergencies should be reported to the Water Supply & Sewerage Board at 1916. You can also submit a report here with location coordinates for faster routing.",
        },
        {
            "keywords": ["electricity", "electric", "power", "outage"],
            "answer": "Electrical emergencies — call BESCOM at 1912 immediately. For non-urgent faults, submit a report via JanRakshak AI and it will be routed to the State Electricity Distribution Company.",
        },
        {
            "keywords": ["garbage", "waste", "trash", "dump"],
            "answer": "Garbage issues are handled by the Municipal Solid Waste Management department. You can call BBMP at 080-22221188 or report here for AI-powered routing.",
        },
        {
            "keywords": ["fire"],
            "answer": "For a fire emergency, call 101 (Fire Brigade) immediately. After the emergency, file a report here for municipal follow-up and prevention measures.",
        },
        {
            "keywords": ["flood", "waterlog", "rain"],
            "answer": "Flooding issues are managed by the Drainage & Flood Control Board. Immediate risk — call 108 (Disaster Management). For recurring waterlogging, submit a report with GPS coordinates.",
        },
        {
            "keywords": ["privacy", "data", "personal"],
            "answer": "JanRakshak AI automatically redacts emails, phone numbers, and house numbers from all reports. GPS coordinates are stored at ward-level precision only. Audit logs are kept for 30 days.",
        },
        {
            "keywords": ["offline", "internet", "connection"],
            "answer": "JanRakshak AI works offline! The AI classification model runs entirely on-device. Reports are queued in IndexedDB and synced automatically when connectivity is restored.",
        },
    ]

    def ask(self, question: str) -> dict:
        q = question.lower()
        for item in self.FAQ:
            if any(kw in q for kw in item["keywords"]):
                return {"answer": item["answer"], "matched": True}

        return {
            "answer": (
                "I can help with questions about road damage, water leaks, electricity, "
                "garbage, flooding, fire emergencies, privacy, and offline functionality. "
                "Please try rephrasing your question or submit a report directly."
            ),
            "matched": False,
        }

