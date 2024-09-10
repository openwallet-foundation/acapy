"""Test Data Integrity Cryptosuites."""

import pytest
from ..cryptosuites import CRYPTOSUITES
from ....core.profile import Profile
from ....wallet.did_method import KEY
from ....wallet.key_type import ED25519


SEED = "testseed000000000000000000000001"


class TestDIProof:
    """Tests for DI sign and verify."""

    @pytest.mark.asyncio
    async def test_eddsa_jcs_2022(self, profile: Profile, in_memory_wallet):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, SEED)
        did = did_info.did
        verification_method = f"{did}#{did.split(':')[-1]}"
        unsecured_document = {"hello": "world"}
        options = {
            "type": "DataIntegrityProof",
            "cryptosuite": "eddsa-jcs-2022",
            "proofPurpose": "assertionMethod",
            "verificationMethod": verification_method,
        }
        suite = CRYPTOSUITES[options["cryptosuite"]](profile=profile)
        secured_document = suite.add_proof(unsecured_document, options)
        assert isinstance(secured_document["proof"], list)
        for proof in secured_document["proof"]:
            assert proof["type"] == "DataIntegrityProof"
            assert proof["cryptosuite"] == "eddsa-jcs-2022"
            assert proof["proofPurpose"] == "assertionMethod"
            assert proof["proofValue"]
            assert proof["verificationMethod"] == verification_method
            assert await suite.verify_proof(unsecured_document, proof)
            bad_proof = proof.copy()
            bad_proof["proofValue"] = bad_proof["proofValue"][:-1]
            assert not await suite.verify_proof(unsecured_document, proof)
