"""Test Data Integrity Cryptosuites."""

import pytest
from ..cryptosuites import CRYPTOSUITES
from ....core.profile import Profile
from ....wallet.did_method import KEY
from ....wallet.key_type import ED25519
from ....wallet.in_memory import InMemoryWallet
from ....core.in_memory import InMemoryProfile
from ....did.did_key import DIDKey


SEED = "testseed000000000000000000000001"
UNSECUURED_DOCUMENT = {"hello": "world"}


class TestDIProof:
    """Tests for DI sign and verify."""

    test_seed = "testseed000000000000000000000001"

    async def asyncSetUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.wallet = InMemoryWallet(self.profile)
        self.eddsa_key_info = await self.wallet.create_signing_key(
            key_type=ED25519, seed=self.test_seed
        )
        self.eddsa_verification_method = DIDKey.from_public_key_b58(
            self.eddsa_key_info.verkey, ED25519
        ).key_id

    @pytest.mark.eddsa_jcs_2022
    async def test_eddsa_jcs_2022_add_proof(self):
        options = {
            "type": "DataIntegrityProof",
            "cryptosuite": "eddsa-jcs-2022",
            "proofPurpose": "assertionMethod",
            "verificationMethod": self.eddsa_verification_method,
        }
        suite = CRYPTOSUITES[options["cryptosuite"]](profile=self.profile)
        secured_document = suite.add_proof(UNSECUURED_DOCUMENT, options)
        proof = secured_document.pop("proof", None)
        assert isinstance(proof, list)
        assert len(proof) == 1
        assert proof["type"] == "DataIntegrityProof"
        assert proof["cryptosuite"] == "eddsa-jcs-2022"
        assert proof["proofPurpose"] == "assertionMethod"
        assert proof["proofValue"]
        assert proof["verificationMethod"] == self.eddsa_verification_method

    @pytest.mark.eddsa_jcs_2022
    async def test_eddsa_jcs_2022_add_proof_set(self):
        options = {
            "type": "DataIntegrityProof",
            "cryptosuite": "eddsa-jcs-2022",
            "proofPurpose": "assertionMethod",
            "verificationMethod": self.eddsa_verification_method,
        }
        suite = CRYPTOSUITES[options["cryptosuite"]](profile=self.profile)
        secured_document = suite.add_proof(UNSECUURED_DOCUMENT, options)
        secured_document = suite.add_proof(secured_document, options)
        proof_set = proof_set.pop("proof", None)
        assert isinstance(proof_set, list)
        assert len(proof_set) == 2
        for proof in proof_set:
            assert proof["type"] == "DataIntegrityProof"
            assert proof["cryptosuite"] == "eddsa-jcs-2022"
            assert proof["proofPurpose"] == "assertionMethod"
            assert proof["proofValue"]
            assert proof["verificationMethod"] == self.eddsa_verification_method

    @pytest.mark.eddsa_jcs_2022
    async def test_eddsa_jcs_2022_verify_proof(self):
        options = {
            "type": "DataIntegrityProof",
            "cryptosuite": "eddsa-jcs-2022",
            "proofPurpose": "assertionMethod",
            "verificationMethod": self.eddsa_verification_method,
        }
        suite = CRYPTOSUITES[options["cryptosuite"]](profile=self.profile)
        secured_document = suite.add_proof(UNSECUURED_DOCUMENT, options)
        proof = secured_document.pop("proof", None)
        assert await suite.verify_proof(secured_document, proof)
        bad_proof = proof.copy()
        bad_proof["proofValue"] = bad_proof["proofValue"][:-1]
        assert not await suite.verify_proof(secured_document, proof)

    @pytest.mark.eddsa_jcs_2022
    async def test_eddsa_jcs_2022_verify_proof_set(self):
        options = {
            "type": "DataIntegrityProof",
            "cryptosuite": "eddsa-jcs-2022",
            "proofPurpose": "assertionMethod",
            "verificationMethod": self.eddsa_verification_method,
        }
        suite = CRYPTOSUITES[options["cryptosuite"]](profile=self.profile)
        secured_document = suite.add_proof(UNSECUURED_DOCUMENT, options)
        secured_document = suite.add_proof(secured_document, options)
        proof_set = secured_document.pop("proof", None)
        for proof in proof_set:
            assert await suite.verify_proof(secured_document, proof)
            bad_proof = proof.copy()
            bad_proof["proofValue"] = bad_proof["proofValue"][:-1]
            assert not await suite.verify_proof(secured_document, proof)
