from django.conf import settings
from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny
from rest_framework.routers import SimpleRouter
from rest_framework.urlpatterns import format_suffix_patterns

# see https://github.com/alanjds/drf-nested-routers
from rest_framework_nested import routers

from icat_hooks.views import HookViewSet, RegistrationViewSet, SubscriptionViewSet

API_METADATA = settings.API_METADATA
schema_view = get_schema_view(
    openapi.Info(
        title=API_METADATA["title"],
        default_version="v1",
        description=API_METADATA["description"],
        terms_of_service=API_METADATA["terms"]["url"],
        contact=openapi.Contact(**API_METADATA["contact"]),
        license=openapi.License(**API_METADATA["license"]),
    ),
    # url="{}/api".format(settings.APPLICATION_URL),
    validators=["flex", "ssv"],
    public=True,
    permission_classes=(AllowAny,),
)

router = SimpleRouter(trailing_slash=False)

# hook management (registration, add/update/delete hooks)
router.register(r"registration", RegistrationViewSet, "Web Hook Registration")
registrations_router = routers.NestedSimpleRouter(
    router, r"registration", lookup="registration"
)
registrations_router.register(
    r"subscriptions", SubscriptionViewSet, basename="subscriptions"
)

urlpatterns = format_suffix_patterns(
    router.urls + registrations_router.urls
)
