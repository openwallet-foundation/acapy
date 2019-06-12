from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.test import TestCase
from icat_hooks import icatrestauth
from rest_framework import exceptions


class IcatAuthBackend_TestCase(TestCase):

    mock_request = Mock()
    mock_username = "mock_user"
    mock_password = "mock_password"

    @patch("icat_hooks.icatrestauth.super.authenticate", autospec=True)
    @patch("icat_hooks.icatrestauth.super")
    def test_authenticate(self, mock_super, mock_authenticate):

        result = icatrestauth.IcatAuthBackend.authenticate(
            self.mock_request, self.mock_username, self.mock_password
        )

        mock_authenticate.assert_called_once_with(
            self.mock_request, self.mock_username, self.mock_password
        )


class IcatRestAuthentication_TestCase(TestCase):

    # base64-encoded: username:password
    mock_username = "username"
    mock_password = "password"
    base64_auth_string = "dXNlcm5hbWU6cGFzc3dvcmQ="
    request_meta = {"HTTP_AUTHORIZATION": "basic " + base64_auth_string}
    mock_request = None
    mock_auth_user = None

    def setUp(self):
        self.mock_auth_user = Mock()
        self.mock_request = HttpRequest()
        self.mock_request.META = self.request_meta

        self.mock_auth_user = get_user_model().objects.create(
            username=self.mock_username, password=self.mock_password, is_active=True
        )

    def test_authenticate_no_creds(self):

        with self.assertRaises(exceptions.AuthenticationFailed):
            icatrestauth.IcatRestAuthentication.authenticate(self, self.mock_request)

    @patch("icat_hooks.icatrestauth.authenticate", autospec=True)
    def test_authenticate_success(self, mock_authenticate):
        mock_authenticate.return_value = self.mock_auth_user

        result = icatrestauth.IcatRestAuthentication.authenticate(
            self, self.mock_request
        )

        self.assertEqual(
            result,
            (self.mock_auth_user, None),
            "The authenticated user should be the same.",
        )
