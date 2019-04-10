from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.permissions import *
from rest_framework import viewsets, mixins
from rest_hooks.models import Hook

from .models.CredentialHook import CredentialHook
from .models.Subscription import Subscription
from .serializers.hooks import (
    HookSerializer,
    RegistrationSerializer,
    SubscriptionSerializer,
)

from .icatrestauth import IcatRestAuthentication

SUBSCRIBERS_GROUP_NAME = "subscriber"


# return authenticated user, or check basic auth info
def get_request_user(request):
    if request.user.is_authenticated:
        print("request_user returning request.user")
        request_user = get_request_user(request)
        return request.user
    if 'HTTP_AUTHORIZATION' in request.META:
        print("request_user checking for basic auth")
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2:
            if auth[0].lower() == "basic":
                print(" ... checking basic auth credentials")
                uname, passwd = base64.b64decode(auth[1]).split(':')
                user = authenticate(username=uname, password=passwd)
                if user is not None and user.is_active:
                    print(" ... authenticated user")
                    request.user = user
                    return user
    print("User is not authenticated and no basic auth")
    return None

class IsOwnerOrCreateOnly(BasePermission):
    """
    Permission check for subscription ownership.
    """

    def has_permission(self, request, view):
        print("IsOwnerOrCreateOnly view permission check ...")
        request_user = get_request_user(request)
        if request.user.is_authenticated:
            print("request.user", request.user)
        else:
            print("request.user is not authenticated")
        ret = super().has_permission(request, view)
        print(" >>> returns ", ret)
        return ret

    def has_object_permission(self, request, view, obj):
        print("IsOwnerOrCreateOnly.has_object_permission()")
        request_user = get_request_user(request)
        if isinstance(obj, get_user_model()):
            print("user", request.user)
            if request.user.is_authenticated:
                print("obj", obj)
                return obj == request.user
            elif request.method == "POST":
                # creating a new user is ok
                return True
        print("IsOwnerOrCreateOnly obj permission check returns False")
        return False


class IsOwnerOnly(BasePermission):
    """
    Permission check for subscription ownership.
    """

    def has_permission(self, request, view):
        print("IsOwnerOnly view permission check ...")
        if request.user.is_authenticated:
            print("request.user", request.user)
        else:
            print("request.user is not authenticated")
        ret = super().has_permission(request, view)
        print(" >>> returns ", ret)
        return ret

    def has_object_permission(self, request, view, obj):
        print("IsOwnerOnly.has_object_permission()")
        if isinstance(obj, Subscription):
            print("user", request.user)
            if request.user.is_authenticated:
                print("obj.owner", obj.owner)
                return obj.owner == request.user
        print("IsOwnerOnly obj permission check returns False")
        return False


class RegistrationCreateViewSet(mixins.CreateModelMixin, 
                                viewsets.GenericViewSet):
    """
    This viewset automatically provides `create` actions.

    {
      "org_name": "Anon Solutions Inc",
      "email": "anon@anon-solutions.ca",
      "target_url": "https://anon-solutions.ca/api/hook",
      "hook_token": "ashdkjahsdkjhaasd88a7d9a8sd9asasda",
      "username": "anon",
      "password": "pass12345"
    }
    """
    serializer_class = RegistrationSerializer
    authentication_classes = ()
    permission_classes = ()

    def get_queryset(self):
        return get_user_model().objects.filter(groups__name=SUBSCRIBERS_GROUP_NAME).all()

    def perform_create(self, serializer):
        serializer.save()


class RegistrationViewSet(mixins.RetrieveModelMixin, 
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    """
    This viewset automatically provides `list`, `retrieve`,
    `update` and `destroy` actions.
    """

    serializer_class = RegistrationSerializer
    lookup_field = "username"
    authentication_classes = (IcatRestAuthentication,)
    permission_classes = (IsOwnerOrCreateOnly,)

    def get_queryset(self):
        get_request_user(self.request)
        if self.request.user.is_authenticated:
            return (
                get_user_model()
                .objects.filter(
                    groups__name=SUBSCRIBERS_GROUP_NAME,
                    username=self.request.user.username,
                )
                .all()
            )
        else:
            raise NotAuthenticated()

    def get_object(self):
        get_request_user(self.request)
        if self.request.user.is_authenticated:
            if self.request.user.username == self.kwargs["username"]:
                obj = get_object_or_404(
                    self.get_queryset(), username=self.kwargs["username"]
                )
                self.check_object_permissions(self.request, obj)
                return obj
            else:
                raise PermissionDenied()
        else:
            raise NotAuthenticated()


class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions.

    {
      "subscription_type": "New",
      "topic_source_id": "BC0123456",
      "credential_type": "registration.registries.ca",
      "target_url": "https://anon-solutions.ca/api/hook",
      "hook_token": "ashdkjahsdkjhaasd88a7d9a8sd9asasda"
    }
    """

    serializer_class = SubscriptionSerializer
    authentication_classes = (IcatRestAuthentication,)
    permission_classes = (IsAuthenticated, IsOwnerOnly,)

    def get_queryset(self):
        if "registration_username" in self.kwargs:
            return Subscription.objects.filter(
                owner__username=self.kwargs["registration_username"]
            ).all()
        elif "username" in self.kwargs:
            return Subscription.objects.filter(
                owner__username=self.kwargs["username"]
            ).all()

    def perform_create(self, serializer):
        subscription = None
        if self.request.user.is_authenticated:
            owner = self.request.user
            subscription = serializer.save(owner=owner)
        else:
            username = None
            if "registration_username" in self.kwargs:
                username = self.kwargs["registration_username"]
            elif "username" in self.kwargs:
                username = self.kwargs["username"]
            else:
                username = serializer["owner"]
            owner = get_user_model().objects.filter(username=username).all()[0]
            subscription = serializer.save(owner=owner)
        if subscription:
            hook = CredentialHook(
                user=owner, event="hookable_cred.added", target=subscription.target_url
            )
            hook.save()
            subscription.hook = hook
            subscription.save()


class HookViewSet(viewsets.ModelViewSet):
    """
    Retrieve, create, update or destroy webhooks.
    """

    queryset = Hook.objects.all()
    model = Hook
    serializer_class = HookSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
