"""
JanRakshak AI — Portal URL Configuration
"""

from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    # Main views
    path("", views.dashboard, name="dashboard"),
    path("report/", views.report_issue, name="report_issue"),
    path("reports/", views.view_reports, name="view_reports"),
    path("emergency/", views.emergency, name="emergency"),

    path("api/submit-report/", views.submit_report, name="submit_report"),
    path("api/preview-analysis/", views.preview_analysis, name="preview_analysis"),
    path("api/upvote-report/", views.upvote_report, name="upvote_report"),
    path("api/analyze-photo/", views.analyze_photo, name="analyze_photo"),
    path("api/ask/", views.ask_assistant, name="ask_assistant"),
    path("api/toggle-spam/<int:report_id>/", views.toggle_spam, name="toggle_spam"),
]
