import datetime
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from icat_hooks import hook_utils
from icat_hooks.models import CredentialHook, HookableCredential, HookUser, Subscription

from api_v2.models import CredentialType, Issuer, Schema

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


class HookUtils_FindAndFireHook_TestCase(TestCase):
    event_name = "testevent"
    instance = None

    newhook = None
    streamhook = None
    topichook = None
    invalidhook = None

    credType = None

    def setUp(self):
        # create user
        user1 = get_user_model().objects.create(username="user1", DID="not:a:did:123")

        # create HookUser
        hookUser = HookUser.objects.create(
            user=user1,
            org_name="myorg1",
            email="email1@mail.me",
            registration_expiry=future_date,
        )

        # creating Issuer
        issuer = Issuer.Issuer.objects.create(
            did="not:a:did:456",
            name="Test Issuer",
            abbreviation="TI",
            email="test@issuer.io",
            url="http://www.issuer.fake.io",
        )

        # creating Schema
        schema = Schema.objects.create(
            name="test-schema", version="0.0.1", origin_did="not:a:did:456"
        )

        # creating CredentialType
        self.credType = CredentialType.objects.create(schema=schema, issuer=issuer)

        # creating CredentialHook
        self.newhook = CredentialHook.objects.create(
            id=1, is_active=True, user_id=user1.id, event=self.event_name + "-new"
        )
        self.newhook.deliver_hook = MagicMock()
        self.streamhook = CredentialHook.objects.create(
            id=2, is_active=True, user_id=user1.id, event=self.event_name + "-stream"
        )
        self.streamhook.deliver_hook = MagicMock()
        self.topichook = CredentialHook.objects.create(
            id=3, is_active=True, user_id=user1.id, event=self.event_name + "-topic"
        )
        self.topichook.deliver_hook = MagicMock()
        self.invalidhook = CredentialHook.objects.create(
            id=4, is_active=True, user_id=user1.id, event=self.event_name + "-invalid"
        )
        self.invalidhook.deliver_hook = MagicMock()
        inactivehook = CredentialHook.objects.create(
            id=5,
            is_active=False,
            user_id=user1.id,
            event=self.event_name + "-deactivated",
        )
        inactivehook.deliver_hook = MagicMock()

        # creating Subscriptions
        Subscription.objects.create(
            hook=self.newhook, subscription_type="New", owner_id=hookUser.id
        )
        Subscription.objects.create(
            hook=self.streamhook,
            subscription_type="Stream",
            owner_id=hookUser.id,
            credential_type=self.credType,
            topic_source_id="123",
        )
        Subscription.objects.create(
            hook=self.topichook,
            subscription_type="Topic",
            owner_id=hookUser.id,
            topic_source_id="123",
        )
        Subscription.objects.create(
            hook=self.invalidhook, subscription_type="Invalid", owner_id=hookUser.id
        )

    @patch("icat_hooks.hook_utils.is_registration_valid", autospec=True)
    def test_invalid_subscription(self, mock_is_reg_valid):

        mock_is_reg_valid.return_value = True

        with self.assertRaises(Exception):
            instance = HookableCredential(topic_status="Invalid")

            hook_utils.find_and_fire_hook(self.event_name + "-invalid", instance)

    @patch("icat_hooks.hook_utils.is_registration_valid", autospec=True)
    @patch("icat_hooks.models.CredentialHook.deliver_hook", autospec=True)
    def test_new_subscription_success(self, mock_deliver_hook, mock_is_reg_valid):
        mock_is_reg_valid.return_value = True

        instance = HookableCredential(topic_status="New")

        hook_utils.find_and_fire_hook(self.event_name + "-new", instance)

        mock_is_reg_valid.assert_called_once_with(self.newhook)

        mock_deliver_hook.assert_called_once_with(self.newhook, instance)

    @patch("icat_hooks.hook_utils.is_registration_valid", autospec=True)
    @patch("icat_hooks.models.CredentialHook.deliver_hook", autospec=True)
    def test_stream_subscription_no_corp_num_no_cred_type(
        self, mock_deliver_hook, mock_is_reg_valid
    ):
        mock_is_reg_valid.return_value = True

        instance = HookableCredential(topic_status="Stream")

        with self.assertRaises(Exception):
            hook_utils.find_and_fire_hook(self.event_name + "-stream", instance)

    @patch("icat_hooks.hook_utils.is_registration_valid", autospec=True)
    @patch("icat_hooks.models.CredentialHook.deliver_hook", autospec=True)
    def test_stream_subscription_no_corp_num(
        self, mock_deliver_hook, mock_is_reg_valid
    ):
        mock_is_reg_valid.return_value = True

        instance = HookableCredential(
            topic_status="Stream", credential_type=self.credType
        )

        with self.assertRaises(Exception):
            hook_utils.find_and_fire_hook(self.event_name + "-stream", instance)

    @patch("icat_hooks.hook_utils.is_registration_valid", autospec=True)
    @patch("icat_hooks.models.CredentialHook.deliver_hook", autospec=True)
    def test_stream_subscription_no_cred_type(
        self, mock_deliver_hook, mock_is_reg_valid
    ):
        mock_is_reg_valid.return_value = True

        instance = HookableCredential(topic_status="Stream", corp_num="123")

        with self.assertRaises(Exception):
            hook_utils.find_and_fire_hook(self.event_name + "-stream", instance)

    @patch("icat_hooks.hook_utils.is_registration_valid", autospec=True)
    @patch("icat_hooks.models.CredentialHook.deliver_hook", autospec=True)
    def test_stream_subscription_success(self, mock_deliver_hook, mock_is_reg_valid):
        mock_is_reg_valid.return_value = True

        instance = HookableCredential(
            topic_status="Stream", corp_num="123", credential_type=self.credType
        )

        hook_utils.find_and_fire_hook(self.event_name + "-stream", instance)

        mock_is_reg_valid.assert_called_once_with(self.streamhook)

        mock_deliver_hook.assert_called_once_with(self.streamhook, instance)

    @patch("icat_hooks.hook_utils.is_registration_valid", autospec=True)
    @patch("icat_hooks.models.CredentialHook.deliver_hook", autospec=True)
    def test_topic_subscription_no_corp_num(self, mock_deliver_hook, mock_is_reg_valid):
        mock_is_reg_valid.return_value = True

        instance = HookableCredential(topic_status="Topic")

        with self.assertRaises(Exception):
            hook_utils.find_and_fire_hook(self.event_name + "-topic", instance)

    @patch("icat_hooks.hook_utils.is_registration_valid", autospec=True)
    @patch("icat_hooks.models.CredentialHook.deliver_hook", autospec=True)
    def test_topic_subscription_success(self, mock_deliver_hook, mock_is_reg_valid):
        mock_is_reg_valid.return_value = True

        instance = HookableCredential(topic_status="Stream", corp_num="123")

        hook_utils.find_and_fire_hook(self.event_name + "-topic", instance)

        mock_is_reg_valid.assert_called_once_with(self.topichook)

        mock_deliver_hook.assert_called_once_with(self.topichook, instance)
