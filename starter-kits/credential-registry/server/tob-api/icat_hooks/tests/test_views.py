import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from api_v2.models.CredentialType import CredentialType
from api_v2.models.Issuer import Issuer
from api_v2.models.Schema import Schema
from icat_hooks.models.Subscription import Subscription


class Icat_Hooks_Views_RegistrationCreateViewSet_TestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(
            username="testuser", password="password"
        )

    def test_create(self):
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post(
            "/hooks/register",
            data={
                "email": "anon@anon-solutions.ca",
                "org_name": "Anon Solutions Inc",
                "target_url": "https://anon-solutions.ca/api/hook",
                "hook_token": "ashdkjahsdkjhaasd88a7d9a8sd9asasda",
                "credentials": {"username": "anon", "password": "pass12345"},
            },
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            "The status code does not match.",
        )
        client.logout()


class Icat_Hooks_Views_RegistrationViewSet_TestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(
            username="testuser", password="password"
        )

        client = APIClient()
        client.force_authenticate(self.user)

        response_1 = client.post(
            "/hooks/register",
            data={
                "email": "anon@anon-solutions.ca",
                "org_name": "Anon Solutions Inc",
                "target_url": "https://anon-solutions.ca/api/hook",
                "hook_token": "ashdkjahsdkjhaasd88a7d9a8sd9asasda",
                "credentials": {"username": "anon", "password": "pass12345"},
            },
            format="json",
        )
        response_2 = client.post(
            "/hooks/register",
            data={
                "email": "esune@mymail.io",
                "org_name": "e-Sun Enterprises",
                "target_url": "https://esune.io/api/hook",
                "hook_token": "ashdkjahsdkjhaasd88a7d9a8sd9asasda",
                "credentials": {"username": "esune", "password": "pass54321"},
            },
            format="json",
        )

        self.registered_user_1 = json.loads(response_1.content)
        self.registered_user_2 = json.loads(response_2.content)

        client.logout()

    def test_get(self):
        client = APIClient()
        client.force_authenticate(
            get_user_model().objects.get(
                username=self.registered_user_1["credentials"]["username"]
            )
        )
        response = client.get("/hooks/registration")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "The response status should be 200.",
        )

        response_content = json.loads(response.content)

        self.assertEqual(
            len(response_content["results"]), 1, "There should be 1 registration."
        )

        client.logout()

    def test_get_by_username(self):
        client = APIClient()
        client.force_authenticate(
            get_user_model().objects.get(
                username=self.registered_user_2["credentials"]["username"]
            )
        )
        response = client.get(
            "/hooks/registration/{}".format(
                self.registered_user_2["credentials"]["username"]
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "The response status should be 200.",
        )

        response_content = json.loads(response.content)

        self.assertEqual(
            response_content["reg_id"], 2, "The registration id does not match."
        )
        self.assertEqual(
            response_content["org_name"],
            "e-Sun Enterprises",
            "The org_name does not match.",
        )

        client.logout()

    def test_patch(self):
        client = APIClient()
        client.force_authenticate(
            get_user_model().objects.get(
                username=self.registered_user_1["credentials"]["username"]
            )
        )
        response = client.patch(
            "/hooks/registration/{}".format(
                self.registered_user_1["credentials"]["username"]
            ),
            data={
                "email": "anon@anon-solutions.ca",
                "org_name": "Anon Solutions Inc",
                "target_url": "https://anon-solutions.ca/api/hook",
                "hook_token": "ashdkjahsdkjhaasd88a7d9a8sd9asasda",
                "credentials": {"username": "anon", "password": "pass12345"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        client.logout()

    def test_delete(self):
        client = APIClient()
        client.force_authenticate(
            get_user_model().objects.get(
                username=self.registered_user_2["credentials"]["username"]
            )
        )
        response = client.delete(
            "/hooks/registration/{}".format(
                self.registered_user_2["credentials"]["username"]
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        client.logout()


class Icat_Hooks_Views_SubscriptionViewSet_TestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(
            username="testuser", password="password"
        )

        self.hook_token_1 = "ashdkjahsdkjhaasd88a7d9a8sd9asasda"
        self.hook_token_2 = "7d9a8sd9asasdaasd88ashdkjahsdkjhaa"

        # create registration users
        client = APIClient()
        client.force_authenticate(self.user)
        response_1 = client.post(
            "/hooks/register",
            data={
                "email": "esune@mymail.io",
                "org_name": "e-Sun Enterprises",
                "target_url": "https://esune.io/api/hook",
                "hook_token": self.hook_token_1,
                "credentials": {"username": "esune", "password": "pass54321"},
            },
            format="json",
        )
        response_2 = client.post(
            "/hooks/register",
            data={
                "email": "anon@anon-solutions.ca",
                "org_name": "Anon Solutions Inc",
                "target_url": "https://anon-solutions.ca/api/hook",
                "hook_token": self.hook_token_2,
                "credentials": {"username": "anon", "password": "pass12345"},
            },
            format="json",
        )

        self.registered_user_1 = json.loads(response_1.content)
        self.registered_user_2 = json.loads(response_2.content)

        client.logout()

        # create issuer, schema, credential type
        self.issuer = Issuer.objects.create(
            did="not:a:did:123456",
            name="Test Issuer",
            abbreviation="TI",
            email="ti@ssue.it",
            url="http://www.tissue.it",
        )
        self.schema = Schema.objects.create(
            name="Test Schema", version="0.1", origin_did="not:a:did:987654"
        )
        self.credential_type = CredentialType.objects.create(
            schema=self.schema, issuer=self.issuer
        )

        # create subscription fro registered_user_2
        self.owner_2 = get_user_model().objects.get(
            username=self.registered_user_2["credentials"]["username"]
        )
        self.reg_user_2_sub = Subscription.objects.create(
            owner=self.owner_2, subscription_type="New", hook_token=self.hook_token_2
        )

    @patch(
        "icat_hooks.serializers.hooks.SubscriptionSerializer.check_live_url",
        autospec=True,
    )
    def test_create(self, mock_url_check):
        mock_url_check.return_value = "SUCCESS"

        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post(
            "/hooks/registration/{}/subscriptions".format(
                self.registered_user_1["credentials"]["username"]
            ),
            data={
                "subscription_type": "New",
                "topic_source_id": "BC0123456",
                "credential_type": "Test Schema",
                "target_url": "https://anon-solutions.ca/api/hook",
                "hook_token": self.hook_token_1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            "The status code does not match.",
        )
        client.logout()

    @patch(
        "icat_hooks.serializers.hooks.SubscriptionSerializer.check_live_url",
        autospec=True,
    )
    def test_get_all(self, mock_url_check):
        mock_url_check.return_value = "SUCCESS"

        # retrieve subscription
        client = APIClient()
        client.force_authenticate(self.owner_2)
        response = client.get(
            "/hooks/registration/{}/subscriptions".format(
                self.registered_user_2["credentials"]["username"]
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "The status code does not match.",
        )

        response_content = json.loads(response.content)

        self.assertEqual(
            len(response_content["results"]),
            1,
            "The number of registrations for the user does not match.",
        )

        self.assertEqual(
            response_content["results"][0]["hook_token"],
            self.hook_token_2,
            "The retrieved registration for the user does not match.",
        )

        client.logout()

    @patch(
        "icat_hooks.serializers.hooks.SubscriptionSerializer.check_live_url",
        autospec=True,
    )
    def test_get_by_id(self, mock_url_check):
        mock_url_check.return_value = "SUCCESS"

        # retrieve subscription
        client = APIClient()
        client.force_authenticate(self.owner_2)
        response = client.get(
            "/hooks/registration/{}/subscriptions/{}".format(
                self.registered_user_2["credentials"]["username"], 1
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "The status code does not match.",
        )

        response_content = json.loads(response.content)

        self.assertEqual(
            response_content["owner"],
            self.registered_user_2["credentials"]["username"],
            "The retrieved registration for the user does not match.",
        )

        client.logout()

    @patch(
        "icat_hooks.serializers.hooks.SubscriptionSerializer.check_live_url",
        autospec=True,
    )
    def test_put(self, mock_url_check):
        mock_url_check.return_value = "SUCCESS"

        # update subscription (full update)
        client = APIClient()
        client.force_authenticate(self.owner_2)
        response = client.put(
            "/hooks/registration/{}/subscriptions/{}".format(
                self.registered_user_2["credentials"]["username"], 1
            ),
            data={
                "subscription_type": "New",
                "topic_source_id": "BC0123456",
                "credential_type": "Test Schema",
                "target_url": "https://123.me/api/lookat",
                "hook_token": self.hook_token_1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "The status code does not match.",
        )

        response_content = json.loads(response.content)

        self.assertEqual(
            response_content["target_url"],
            "https://123.me/api/lookat",
            "The retrieved registration for the user does not match.",
        )

        client.logout()

    @patch(
        "icat_hooks.serializers.hooks.SubscriptionSerializer.check_live_url",
        autospec=True,
    )
    def test_patch(self, mock_url_check):
        mock_url_check.return_value = "SUCCESS"

        # patch subscription (partial update)
        client = APIClient()
        client.force_authenticate(self.owner_2)
        response = client.put(
            "/hooks/registration/{}/subscriptions/{}".format(
                self.registered_user_2["credentials"]["username"], 1
            ),
            data={
                "subscription_type": "New",
                "topic_source_id": "AB987654",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "The status code does not match.",
        )

        response_content = json.loads(response.content)

        self.assertEqual(
            response_content["topic_source_id"],
            "AB987654",
            "The retrieved registration for the user does not match.",
        )

        client.logout()

    @patch(
        "icat_hooks.serializers.hooks.SubscriptionSerializer.check_live_url",
        autospec=True,
    )
    def test_delete(self, mock_url_check):
        mock_url_check.return_value = "SUCCESS"

        # delete subscription
        client = APIClient()
        client.force_authenticate(
            get_user_model().objects.get(
                username=self.registered_user_2["credentials"]["username"]
            )
        )
        response = client.delete(
            "/hooks/registration/{}/subscriptions/{}".format(
                self.registered_user_2["credentials"]["username"], 1
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        client.logout()
