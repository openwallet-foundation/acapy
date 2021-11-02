from asynctest import TestCase

from ..check import get_properties_without_context
from ...tests.document_loader import custom_document_loader

VALID_INPUT_DOC = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/citizenship/v1",
        "https://w3id.org/security/bbs/v1",
    ],
    "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
    "type": ["PermanentResidentCard", "VerifiableCredential"],
    "description": "Government of Example Permanent Resident Card.",
    "identifier": "83627465",
    "name": "Permanent Resident Card",
    "credentialSubject": {
        "id": "did:example:b34ca6cd37bbf23",
        "type": ["Person", "PermanentResident"],
        "familyName": "SMITH",
        "gender": "Male",
        "givenName": "JOHN",
    },
    "expirationDate": "2029-12-03T12:19:52Z",
    "issuanceDate": "2019-12-03T12:19:52Z",
    "issuer": "did:example:489398593",
    "proof": {
        "type": "BbsBlsSignatureProof2020",
        "nonce": "wrmPiSRm+iBqnGBXz+/37LLYRZWirGgIORKHIkrgWVnHtb4fDe/4ZPZaZ+/RwGVJYYY=",
        "proofValue": "ABkB/wbvt6213E9eJ+aRGbdG1IIQtx+IdAXALLNg2a5ENSGOIBxRGSoArKXwD/diieDWG6+0q8CWh7CViUqOOdEhYp/DonzmjoWbWECalE6x/qtyBeE7W9TJTXyK/yW6JKSKPz2ht4J0XLV84DZrxMF4HMrY7rFHvdE4xV7ULeC9vNmAmwYAqJfNwY94FG2erg2K2cg0AAAAdLfutjMuBO0JnrlRW6O6TheATv0xZZHP9kf1AYqPaxsYg0bq2XYzkp+tzMBq1rH3tgAAAAIDTzuPazvFHijdzuAgYg+Sg0ziF+Gw5Bz8r2cuvuSg1yKWqW1dM5GhGn6SZUpczTXuZuKGlo4cZrwbIg9wf4lBs3kQwWULRtQUXki9izmznt4Go98X/ElOguLLum4S78Gehe1ql6CXD1zS5PiDXjDzAAAACWz/sbigWpPmUqNA8YUczOuzBUvzmkpjVyL9aqf1e7rSZmN8CNa6dTGOzgKYgDGoIbSQR8EN8Ld7kpTIAdi4YvNZwEYlda/BR6oSrFCquafz7s/jeXyOYMsiVC53Zls9KEg64tG7n90XuZOyMk9RAdcxYRGligbFuG2Ap+rQ+rrELJaW7DWwFEI6cRnitZo6aS0hHmiOKKtJyA7KFbx27nBGd2y3JCvgYO6VUROQ//t3F4aRVI1U53e5N3MU+lt9GmFeL+Kv+2zV1WssScO0ZImDGDOvjDs1shnNSjIJ0RBNAo2YzhFKh3ExWd9WbiZ2/USSyomaSK4EzdTDqi2JCGdqS7IpooKSX/1Dp4K+d8HhPLGNLX4yfMoG9SnRfRQZZQ==",
        "verificationMethod": "did:example:489398593#test",
        "proofPurpose": "assertionMethod",
        "created": "2020-10-16T23:59:31Z",
    },
}

INVALID_INPUT_DOC = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/citizenship/v1",
    ],
    "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
    "type": ["PermanentResidentCard", "VerifiableCredential"],
    "description": "Government of Example Permanent Resident Card.",
    "identifier": "83627465",
    "name": "Permanent Resident Card",
    "credentialSubject": [
        {
            "id": "did:example:b34ca6cd37bbf23",
            "type": ["Person", "PermanentResident"],
            "familyName": "SMITH",
            "gender": "Male",
            "givenName": "JOHN",
        },
        {
            "some_random": "value",
        },
    ],
    "expirationDate": "2029-12-03T12:19:52Z",
    "issuanceDate": "2019-12-03T12:19:52Z",
    "issuer": "did:example:489398593",
    "proof": {
        "type": "BbsBlsSignatureProof2020",
        "nonce": "wrmPiSRm+iBqnGBXz+/37LLYRZWirGgIORKHIkrgWVnHtb4fDe/4ZPZaZ+/RwGVJYYY=",
        "proofValue": "ABkB/wbvt6213E9eJ+aRGbdG1IIQtx+IdAXALLNg2a5ENSGOIBxRGSoArKXwD/diieDWG6+0q8CWh7CViUqOOdEhYp/DonzmjoWbWECalE6x/qtyBeE7W9TJTXyK/yW6JKSKPz2ht4J0XLV84DZrxMF4HMrY7rFHvdE4xV7ULeC9vNmAmwYAqJfNwY94FG2erg2K2cg0AAAAdLfutjMuBO0JnrlRW6O6TheATv0xZZHP9kf1AYqPaxsYg0bq2XYzkp+tzMBq1rH3tgAAAAIDTzuPazvFHijdzuAgYg+Sg0ziF+Gw5Bz8r2cuvuSg1yKWqW1dM5GhGn6SZUpczTXuZuKGlo4cZrwbIg9wf4lBs3kQwWULRtQUXki9izmznt4Go98X/ElOguLLum4S78Gehe1ql6CXD1zS5PiDXjDzAAAACWz/sbigWpPmUqNA8YUczOuzBUvzmkpjVyL9aqf1e7rSZmN8CNa6dTGOzgKYgDGoIbSQR8EN8Ld7kpTIAdi4YvNZwEYlda/BR6oSrFCquafz7s/jeXyOYMsiVC53Zls9KEg64tG7n90XuZOyMk9RAdcxYRGligbFuG2Ap+rQ+rrELJaW7DWwFEI6cRnitZo6aS0hHmiOKKtJyA7KFbx27nBGd2y3JCvgYO6VUROQ//t3F4aRVI1U53e5N3MU+lt9GmFeL+Kv+2zV1WssScO0ZImDGDOvjDs1shnNSjIJ0RBNAo2YzhFKh3ExWd9WbiZ2/USSyomaSK4EzdTDqi2JCGdqS7IpooKSX/1Dp4K+d8HhPLGNLX4yfMoG9SnRfRQZZQ==",
        "verificationMethod": "did:example:489398593#test",
        "proofPurpose": "assertionMethod",
        "created": "2020-10-16T23:59:31Z",
    },
}

VALID_VACCINATION_DOC = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/security/bbs/v1",
        "https://w3id.org/vaccination/v1",
    ],
    "type": ["VerifiableCredential", "VaccinationCertificate"],
    "issuer": "replace_me",
    "id": "urn:uvci:af5vshde843jf831j128fj",
    "name": "COVID-19 Vaccination Certificate",
    "description": "COVID-19 Vaccination Certificate",
    "issuanceDate": "2019-12-03T12:19:52Z",
    "expirationDate": "2029-12-03T12:19:52Z",
    "credentialSubject": {
        "type": "VaccinationEvent",
        "batchNumber": "1183738569",
        "administeringCentre": "MoH",
        "healthProfessional": "MoH",
        "countryOfVaccination": "NZ",
        "recipient": {
            "type": "VaccineRecipient",
            "givenName": "JOHN",
            "familyName": "SMITH",
            "gender": "Male",
            "birthDate": "1958-07-17",
        },
        "vaccine": {
            "type": "Vaccine",
            "disease": "COVID-19",
            "atcCode": "J07BX03",
            "medicinalProductName": "COVID-19 Vaccine Moderna",
            "marketingAuthorizationHolder": "Moderna Biotech",
        },
    },
}


INVALID_VACCINATION_DOC = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/security/bbs/v1",
        "https://w3id.org/vaccination/v1",
    ],
    "type": ["VerifiableCredential", "VaccinationCertificate"],
    "issuer": "replace_me",
    "id": "urn:uvci:af5vshde843jf831j128fj",
    "name": "COVID-19 Vaccination Certificate",
    "description": "COVID-19 Vaccination Certificate",
    "issuanceDate": "2019-12-03T12:19:52Z",
    "expirationDate": "2029-12-03T12:19:52Z",
    "credentialSubject": {
        "type": "VaccinationEvent",
        "batchNumber": "1183738569",
        "administeringCentre": "MoH",
        "healthProfessional": "MoH",
        "countryOfVaccination": "NZ",
        "recipient": {
            "type": "VaccineRecipient",
            "givenName": "JOHN",
            "familyName": "SMITH",
            "gender": "Male",
            "birthDate": "1958-07-17",
            "nonExistent": "hello",
        },
        "vaccine": {
            "type": "Vaccine",
            "disease": "COVID-19",
            "atcCode": "J07BX03",
            "medicinalProductName": "COVID-19 Vaccine Moderna",
            "marketingAuthorizationHolder": "Moderna Biotech",
            "nonExistent": {"hello": "goodbye"},
        },
    },
}


class TestCheck(TestCase):
    def test_get_properties_without_context_valid(self):
        assert (
            get_properties_without_context(VALID_INPUT_DOC, custom_document_loader)
            == []
        )

    def test_get_properties_without_context_invalid(self):
        # document has extra property some_random and
        # is missing the bbs context
        assert get_properties_without_context(
            INVALID_INPUT_DOC, custom_document_loader
        ) == [
            "credentialSubject[1].some_random",
            "proof.nonce",
            "proof.proofValue",
            "proof.verificationMethod",
            "proof.proofPurpose",
            "proof.created",
        ]

    def test_get_properties_without_context_vaccination_valid(self):
        assert (
            get_properties_without_context(
                VALID_VACCINATION_DOC, custom_document_loader
            )
            == []
        )

    def test_get_properties_without_context_vaccination_invalid(self):
        assert get_properties_without_context(
            INVALID_VACCINATION_DOC, custom_document_loader
        ) == [
            "credentialSubject.recipient.nonExistent",
            "credentialSubject.vaccine.nonExistent",
        ]
