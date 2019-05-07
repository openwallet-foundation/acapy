import base64

from django.http import HttpResponse
from django.contrib.auth import authenticate
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from rest_framework.authentication import BasicAuthentication
from rest_framework import exceptions
from rest_framework import authentication


class IcatAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None):
        # Check the username/password and return a user.
        user = super(IcatAuthBackend, self).authenticate(request, username, password)
        return user


class IcatRestAuthentication(BasicAuthentication):

    # TODO: check whether this is being used or not, and whether it is a duplicate of views.get_request_user
    def authenticate(self, request):
        try:
            # Check for valid basic auth header
            if "HTTP_AUTHORIZATION" in request.META:
                (authmeth, auth) = request.META["HTTP_AUTHORIZATION"].split(" ", 1)
                if authmeth.lower() == "basic":
                    auth = base64.b64decode(auth).decode("utf-8")
                    (username, password) = auth.split(":", 1)
                    user = authenticate(username=username, password=password)
                    if user is not None and user.is_active:
                        request.user = user
                        return (user, None)  # authentication successful
        except Exception as e:
            # if we get any exceptions, treat as auth failure
            pass

        raise exceptions.AuthenticationFailed("No credentials provided.")
