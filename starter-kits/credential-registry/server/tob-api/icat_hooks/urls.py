from icat_hooks.views import (
    RegistrationCreateViewSet,
    RegistrationViewSet,
    SubscriptionViewSet,
)
from rest_framework.routers import SimpleRouter
from rest_framework.urlpatterns import format_suffix_patterns

# see https://github.com/alanjds/drf-nested-routers
from rest_framework_nested import routers

router = SimpleRouter(trailing_slash=False)

# hook management (registration, add/update/delete hooks)
router.register(r"register", RegistrationCreateViewSet, "Web Hook Registration")
router.register(r"registration", RegistrationViewSet, "Web Hook Registration")
registrations_router = routers.NestedSimpleRouter(
    router, r"registration", lookup="registration"
)
registrations_router.register(
    r"subscriptions", SubscriptionViewSet, basename="subscriptions"
)

urlpatterns = format_suffix_patterns(router.urls + registrations_router.urls)
