from unittest import TestCase

from ...models.cred_detail import LDProofVCDetail
from ...models.cred_detail_options import LDProofVCDetailOptions

VC_DETAIL_OPTIONS = {
    "proofType": "Ed25519Signature2018",
    "proofPurpose": "assertionMethod",
    "created": "2010-01-01T19:73:24Z",
    "domain": "example.com",
    "challenge": "019a5321-1c1f-4031-8b9b-8c0234be7d78",
    "credentialStatus": {"type": "CredentialStatusList2017"},
}

VC_DETAIL_CREDENTIAL = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/citizenship/v1",
        "https://w3id.org/security/bbs/v1",
    ],
    "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
    "type": ["VerifiableCredential", "PermanentResidentCard"],
    "issuer": "did:example:489398593",
    "identifier": "83627465",
    "name": "Permanent Resident Card",
    "description": "Government of Example Permanent Resident Card.",
    "issuanceDate": "2019-12-03T12:19:52Z",
    "expirationDate": "2029-12-03T12:19:52Z",
    "credentialSubject": {
        "id": "did:example:b34ca6cd37bbf23",
        "type": ["PermanentResident", "Person"],
        "givenName": "JOHN",
        "familyName": "SMITH",
        "gender": "Male",
        "image": "data:image/png;base64,iVBORw0KGgokJggg==",
        "residentSince": "2015-01-01",
        "lprCategory": "C09",
        "lprNumber": "999-999-999",
        "commuterClassification": "C1",
        "birthCountry": "Bahamas",
        "birthDate": "1958-07-17",
    },
}

VC_DETAIL = {"credential": VC_DETAIL_CREDENTIAL, "options": VC_DETAIL_OPTIONS}


class TestLDProofVCDetail(TestCase):
    """LDProofVCDetail correctness proof tests"""

    def test_serde(self):
        """Test de/serialization."""
        detail = LDProofVCDetail.deserialize(VC_DETAIL)
        assert type(detail) == LDProofVCDetail

        detail_dict = detail.serialize()
        assert detail_dict == VC_DETAIL


class TestLDProofVCDetailOptions(TestCase):
    """LDProofVCDetail correctness proof tests"""

    def test_serde(self):
        """Test de/serialization."""
        detail_options = LDProofVCDetailOptions.deserialize(VC_DETAIL_OPTIONS)
        assert type(detail_options) == LDProofVCDetailOptions

        detail_options_dict = detail_options.serialize()
        assert detail_options_dict == VC_DETAIL_OPTIONS
