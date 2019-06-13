from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api_v2.models.CredentialType import CredentialType
from api_v2.models.Issuer import Issuer
from api_v2.models.Schema import Schema


class IssuerViewSetTest(APITestCase):
    def setUp(self):
        # create test issuers
        issuer1 = Issuer.objects.create(
            did="not:a:did:456",
            name="Test Issuer 1",
            abbreviation="TI-1",
            email="test1@issuer.io",
            url="http://www.issuer-1.fake.io",
            logo_b64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        )
        Issuer.objects.create(
            did="not:a:did:123",
            name="Test Issuer 2",
            abbreviation="TI-2",
            email="test2@issuer.io",
            url="http://www.issuer-2.fake.io",
        )

        # create test schema/credential type and bind it to issuer1
        # creating Schema
        schema = Schema.objects.create(
            name="test-schema", version="0.0.1", origin_did="not:a:did:456"
        )

        # creating CredentialType
        self.credType = CredentialType.objects.create(
            schema=schema, issuer=issuer1, credential_def_id="123456"
        )

    def test_get_issuer_list(self):
        url = reverse("issuer-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 2)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["name"], "Test Issuer 1")
        self.assertEqual(response.data["results"][1]["name"], "Test Issuer 2")

    def test_get_issuer_by_id(self):
        url = reverse("issuer-list")
        response = self.client.get(url + "/1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], 1)
        self.assertEqual(response.data["did"], "not:a:did:456")

    def test_get_issuer_credentialtype(self):
        url = reverse("issuer-list")
        response = self.client.get(url + "/1/credentialtype")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["issuer"]["did"], "not:a:did:456")
        self.assertEqual(response.data[0]["credential_def_id"], "123456")
        self.assertEqual(response.data[0]["schema"]["name"], "test-schema")

    def test_get_issuer_logo(self):
        url = reverse("issuer-list")
        response1 = self.client.get(url + "/1/logo")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        response2 = self.client.get(url + "/2/logo")
        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)
