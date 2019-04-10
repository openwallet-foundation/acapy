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
        print(" >>> Test auth for", username)
        user = super(IcatAuthBackend, self).authenticate(request, username, password)
        if user:
            print(" >>> Authenticated", username, user)
        else:
            print(" >>> Not authenticated", username)
        return user


class IcatRestAuthentication(BasicAuthentication):

    def authenticate(self, request):
        try:
            # Check for valid basic auth header
            print(" >>> try to basic authenticate ", request.META)
            if 'HTTP_AUTHORIZATION' in request.META:
                (authmeth, auth) = request.META['HTTP_AUTHORIZATION'].split(' ',1)
                print(" >>> ", authmeth.lower())
                if authmeth.lower() == "basic":
                    auth = base64.b64decode(auth).decode('utf-8')
                    (username, password) = auth.split(':',1)
                    print(" >>> ", username, password)
                    user = authenticate(username=username, password=password)
                    if user is not None and user.is_active:
                        print(" >>> authentication success!!!")
                        request.user = user
                        return (user, None)  # authentication successful
            else:
                print(" >>> No basic auth headers")
            print(" >>> authentication failed")
        except Exception as e:
            # if we get any exceptions, treat as auth failure
            print(" >>> some authentication exception", e)
            pass

        raise exceptions.AuthenticationFailed('No credentials provided.')

