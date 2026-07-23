"""
JanRakshak AI — Admin Panel URL Configuration
All admin routes are namespaced under 'admin_panel'.
"""

from django.urls import path
from portal import admin_views

app_name = "admin_panel"

urlpatterns = [
    # Auth
    path("login/",  admin_views.admin_login,  name="login"),
    path("logout/", admin_views.admin_logout, name="logout"),

    # Main pages
    path("",              admin_views.admin_dashboard, name="dashboard"),
    path("reports/",      admin_views.admin_reports,   name="reports"),
    path("analytics/",    admin_views.admin_analytics,  name="analytics"),
    path("audit-log/",    admin_views.admin_audit_log,  name="audit_log"),
    path("settings/",     admin_views.admin_settings,   name="settings"),

    # API endpoints
    path("api/resolve/<int:report_id>/", admin_views.api_resolve_report, name="resolve_report"),
    path("api/delete/<int:report_id>/",  admin_views.api_delete_report,  name="delete_report"),
    path("api/detail/<int:report_id>/",  admin_views.api_report_detail,  name="report_detail"),
    path("api/export/csv/",              admin_views.api_export_csv,      name="export_csv"),
]
