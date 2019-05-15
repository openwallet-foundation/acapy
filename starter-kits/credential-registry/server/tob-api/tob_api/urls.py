"""
Definition of urls for tob_api.
"""

from django.views.generic import RedirectView
from django.urls import include, path
from . import views

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = [
    path("", RedirectView.as_view(url="api/v2/")),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api/v2/", include("api_v2.urls")),
    path("health", views.health),
    path("hooks/", include("icat_hooks.urls")),
]
