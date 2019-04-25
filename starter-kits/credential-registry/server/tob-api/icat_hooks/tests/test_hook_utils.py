import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from icat_hooks import hook_utils
from icat_hooks.models import CredentialHook, HookUser

today = datetime.datetime.now().date()
past_date = datetime.datetime.now() - datetime.timedelta(days=2)
future_date = datetime.datetime.now() + datetime.timedelta(days=2)


class HookUtils_ValidRegistration_TestCase(TestCase):
    def setUp(self):
        # create user
        user1 = get_user_model().objects.create(username="user1", DID="not:a:did:123")
        user2 = get_user_model().objects.create(username="user2", DID="not:a:did:456")

        # create HookUser
        HookUser.objects.create(
            user=user1,
            org_name="myorg1",
            email="email1@mail.me",
            registration_expiry=past_date,
        )
        HookUser.objects.create(
            user=user2,
            org_name="myorg2",
            email="email2@mail.me",
            registration_expiry=today,
        )

        # creating CredentialHook
        CredentialHook.objects.create(id=1, is_active=True, user_id=user1.id)
        CredentialHook.objects.create(id=2, is_active=True, user_id=user2.id)

    def test_registration_expired(self):

        with patch("icat_hooks.hook_utils.deactivate_hook") as deactivate_hook:

            credhook = CredentialHook.objects.get(id=1)
            isValid = hook_utils.is_registration_valid(credhook)
            self.assertFalse(
                isValid, "The CredentialHook registration_date has expired."
            )

            deactivate_hook.assert_called_once_with(1)

    def test_registration_valid(self):

        with patch("icat_hooks.hook_utils.deactivate_hook") as deactivate_hook:

            credhook = CredentialHook.objects.get(id=2)
            isValid = hook_utils.is_registration_valid(credhook)
            self.assertTrue(isValid, "The CredentialHook registration_date is valid.")

            deactivate_hook.assert_not_called()

    def test_deactivate_hook(self):
        credhook_before = CredentialHook.objects.get(id=1)
        self.assertTrue(credhook_before.is_active, "The credential hook is active.")

        hook_utils.deactivate_hook(1)

        credhook_after = CredentialHook.objects.get(id=1)
        self.assertFalse(
            credhook_after.is_active, "The credential hook was deactivate."
        )
