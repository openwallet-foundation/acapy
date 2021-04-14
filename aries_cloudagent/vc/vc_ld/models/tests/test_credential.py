from unittest import TestCase

from marshmallow.utils import INCLUDE

from ...models.credential import VerifiableCredential
from ...models.linked_data_proof import LDProof

CREDENTIAL = {
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


VC_PROOF = {
    "type": "BbsBlsSignatureProof2020",
    "created": "2020-12-14T03:11:30Z",
    "nonce": "CF69iO3nfvqRsRBNElE8b4wO39SyJHPM7Gg1nExltW5vSfQA1lvDCR/zXX1To0/4NLo=",
    "proofPurpose": "assertionMethod",
    "proofValue": "AA0f/7dHROgM2jXZiK0UmY5956/26qbbWF1sKgTMLx1NWEJqrE2ptwlREsxxrqZDRy5pxIFeSxDe08yWxDIk7zefzbwHd04hfbs0oaE2e9TMxIhfUZnct5Br7XenOwpZkkW1d7nt/yUFclgLCAIg+8B3UDpsuzv4rAJ3bTvD69nrMJPwC+Ao7meBgPcAaubNirSqrgAAAHSqzxvoLIRtX8mcq90yIHHuAcThiP63ChKE9c49pJboQ5FBA1aiMIIAJ+J7JPZtBGUAAAACIly7gNiA2nXJAVTKNepEQOtdyEU1gqExcaxWhMgX6nBCRGCwypy5lDDj2XWsvcuzPcvrpvaBxIBvTBAVjKDODaExOe1FKwA2t6F80wvt1BrEQpa5mG9YsI7Hw0wwl+c0SekC/WYlVW0oFjdICH+ZsAAAAAJlYX1Br69N/IAemIkmBvU/7bcIGssDcGL4hNzuTe0a8FnXYhUHyYmnMYFgZMv2ht2nMZiSwAugP2y3dFAU99bU",
    "verificationMethod": "did:example:489398593#test",
}

VERIFIABLE_CREDENTIAL = {**CREDENTIAL, "proof": VC_PROOF}


class TestLinkedDataProof(TestCase):
    """LinkedDataProof tests"""

    def test_serde(self):
        """Test de/serialization."""
        proof = LDProof.deserialize(VC_PROOF)
        assert type(proof) == LDProof

        proof_dict = proof.serialize()
        assert proof_dict == VC_PROOF


class TestVerifiableCredential(TestCase):
    """VerifiableCredential tests"""

    def test_serde_credential(self):
        """Test de/serialization."""
        credential = VerifiableCredential.deserialize(CREDENTIAL, unknown=INCLUDE)
        assert type(credential) == VerifiableCredential

        credential_dict = credential.serialize()
        assert credential_dict == CREDENTIAL

    def test_serde_verifiable_credential(self):
        """Test de/serialization."""
        credential = VerifiableCredential.deserialize(
            VERIFIABLE_CREDENTIAL, unknown=INCLUDE
        )
        assert type(credential) == VerifiableCredential

        credential_dict = credential.serialize()
        assert credential_dict == VERIFIABLE_CREDENTIAL