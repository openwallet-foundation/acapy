import json
import uuid
from unittest import IsolatedAsyncioTestCase

import copy
import pytest
from aiohttp import web

from ...routes import store_credential_route

VALID_VC = {
    "@context": [
      "https://www.w3.org/ns/credentials/v2",
      "https://w3id.org/security/suites/ed25519-2020/v1"
    ],
    "type": [
      "VerifiableCredential"
    ],
    "issuer": "did:key:z6MksJQETYp2tT6PQhs1pmhqH8c77C8Ki6s23pWYPtC5Z2je",
    "credentialSubject": {
      "name": "Alice"
    },
    "proof": {
      "type": "Ed25519Signature2020",
      "proofPurpose": "assertionMethod",
      "verificationMethod": "did:key:z6MksJQETYp2tT6PQhs1pmhqH8c77C8Ki6s23pWYPtC5Z2je#z6MksJQETYp2tT6PQhs1pmhqH8c77C8Ki6s23pWYPtC5Z2je",
      "created": "2025-07-16T15:20:23+00:00",
      "proofValue": "z2uey5H4Bz9NHQezA6i2NNpvyrDNspHaFei3hcNTCqjAJi3ocs4DzzTbnXRGs5a6LMp9uNo7RyqtBcBmrstyAg1ML"
    }
}
INVALID_VC = copy.deepcopy(VALID_VC)
INVALID_VC['proof']['proofValue'] = "unsecured"

@pytest.mark.vc
class TestVcApiRoutes(IsolatedAsyncioTestCase):
    
    async def test_credentials_store(self):
        response = store_credential_route(VALID_VC)
        assert response
            
    async def test_credentials_store_unsecured(self):
        options = {
            'credentialId': str(uuid.uuid4()),
            'verify': False
        }
        response = store_credential_route(INVALID_VC, options)
        assert response

        with self.assertRaises(web.HTTPBadRequest):
            response = store_credential_route(INVALID_VC)