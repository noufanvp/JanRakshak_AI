"""
JanRakshak AI — Root URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.http import HttpResponse
import os


def serve_serviceworker(request):
    """Serve the PWA service worker from root path for full-scope coverage."""
    sw_dirs = getattr(settings, "STATICFILES_DIRS", [])
    sw_path = None
    for d in sw_dirs:
        candidate = os.path.join(d, "pwa", "serviceworker.js")
        if os.path.exists(candidate):
            sw_path = candidate
            break
    if not sw_path:
        fallback = os.path.join(settings.STATIC_ROOT or "", "pwa", "serviceworker.js")
        if os.path.exists(fallback):
            sw_path = fallback
    if sw_path:
        with open(sw_path, "rb") as f:
            return HttpResponse(f.read(), content_type="application/javascript")
    return HttpResponse("// Service Worker not found", content_type="application/javascript", status=404)


urlpatterns = [
    # Django built-in admin
    path("django-admin/", admin.site.urls),

    # Portal (public-facing app)
    path("", include("portal.urls")),

    # Custom admin panel
    path("admin-panel/", include("portal.admin_urls")),

    # PWA — service worker served from root for full-scope coverage
    path("serviceworker.js", serve_serviceworker, name="serviceworker"),

    # PWA offline fallback page
    path(
        "pwa/offline/",
        TemplateView.as_view(template_name="pwa/offline.html"),
        name="pwa_offline",
    ),
]

# Serve static & media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    if hasattr(settings, "MEDIA_ROOT"):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

