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
        schema = Schema.objects.create(
            name="test-schema", version="0.0.1", origin_did="not:a:did:456"
        )

        # create test CredentialType and bind it to issuer1
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

    def test_get_issuer_logo_success(self):
        url = reverse("issuer-list")
        response1 = self.client.get(url + "/1/logo")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        response2 = self.client.get(url + "/2/logo")
        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)


class SchemaViewSetTest(APITestCase):
    def setUp(self):
        # create test schemas
        Schema.objects.create(
            name="test-schema-1", version="0.5.0", origin_did="not:a:did:123"
        )
        Schema.objects.create(
            name="test-schema-2", version="1.0.0", origin_did="not:a:did:456"
        )
        Schema.objects.create(
            name="test-schema-3", version="0.2.1", origin_did="not:a:did:123"
        )
        Schema.objects.create(
            name="test-schema-4", version="3.0.1", origin_did="not:a:did:123"
        )
        Schema.objects.create(
            name="test-schema-5", version="0.5.0", origin_did="not:a:did:789"
        )

    def test_get_schema_list_no_filters(self):
        url = reverse("schema-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 5)
        self.assertEqual(len(response.data["results"]), 5)

    def test_get_schema_filter_by_id(self):
        url = reverse("schema-list")
        response = self.client.get(url + "?id=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_get_schema_filter_by_name(self):
        url = reverse("schema-list")
        response = self.client.get(url + "?name=test-schema-2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_get_schema_filter_by_version(self):
        url = reverse("schema-list")
        response = self.client.get(url + "?version=0.5.0")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_get_schema_filter_by_origin_did(self):
        url = reverse("schema-list")
        response = self.client.get(url + "?origin_did=not:a:did:123")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 3)
        self.assertEqual(len(response.data["results"]), 3)

    def test_get_schema_by_id(self):
        url = reverse("schema-list")
        response = self.client.get(url + "/3")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], 3)
        self.assertEqual(response.data["origin_did"], "not:a:did:123")
