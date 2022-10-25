from asynctest import TestCase, mock as async_mock
import pytest

from aries_cloudagent.wallet.key_type import BLS12381G2

from .....did.did_key import DIDKey
from .....wallet.key_pair import KeyType
from .....wallet.in_memory import InMemoryWallet
from .....core.in_memory import InMemoryProfile
from ....tests.document_loader import custom_document_loader
from ....tests.data import (
    TEST_LD_DOCUMENT_SIGNED_BBS,
    TEST_LD_DOCUMENT_PROOF_BBS,
    TEST_LD_DOCUMENT_BAD_PARTIAL_PROOF_BBS,
    TEST_LD_DOCUMENT_PARTIAL_PROOF_BBS,
    TEST_LD_DOCUMENT_REVEAL_ALL,
    TEST_LD_DOCUMENT_REVEAL,
    TEST_VC_DOCUMENT_SIGNED_BBS,
    TEST_VC_DOCUMENT_REVEAL,
    TEST_VC_DOCUMENT_NESTED_PARTIAL_PROOF_BBS,
    TEST_VC_DOCUMENT_NESTED_PROOF_BBS,
    TEST_VC_DOCUMENT_NESTED_SIGNED_BBS,
    TEST_VC_DOCUMENT_PARTIAL_PROOF_BBS,
    TEST_VC_DOCUMENT_NESTED_REVEAL,
)
from ....vc_ld import derive_credential, verify_credential

from ...crypto.wallet_key_pair import WalletKeyPair
from ...purposes.assertion_proof_purpose import AssertionProofPurpose
from ...error import LinkedDataProofException
from ...ld_proofs import verify, derive

from ..bbs_bls_signature_proof_2020 import BbsBlsSignatureProof2020


@pytest.mark.ursa_bbs_signatures
class TestBbsBlsSignatureProof2020(TestCase):
    test_seed = "testseed000000000000000000000001"

    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.wallet = InMemoryWallet(self.profile)
        self.key = await self.wallet.create_signing_key(
            key_type=BLS12381G2, seed=self.test_seed
        )
        self.verification_method = DIDKey.from_public_key_b58(
            self.key.verkey, BLS12381G2
        ).key_id

        self.key_pair = WalletKeyPair(wallet=self.wallet, key_type=BLS12381G2)

    async def test_derive_ld_proofs(self):
        derived = await derive(
            document=TEST_LD_DOCUMENT_SIGNED_BBS,
            reveal_document=TEST_LD_DOCUMENT_REVEAL,
            document_loader=custom_document_loader,
            suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
        )

        assert derived

    async def test_verify_derived_x_bad_proof(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_BAD_PARTIAL_PROOF_BBS,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert not result.verified

    async def test_derive_x_unsigned_claims(self):
        doc = {**TEST_LD_DOCUMENT_SIGNED_BBS, "unsigned_claim": True}

        with self.assertRaises(Exception) as context:
            await derive(
                document=doc,
                reveal_document=TEST_LD_DOCUMENT_REVEAL_ALL,
                document_loader=custom_document_loader,
                suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
            )
        assert "The messages and signature do not match" in str(context.exception)

    async def test_derive_x_modified_claims(self):
        doc = {**TEST_LD_DOCUMENT_SIGNED_BBS, "email": "bad@example.com"}

        with self.assertRaises(Exception) as context:
            await derive(
                document=doc,
                reveal_document=TEST_LD_DOCUMENT_REVEAL_ALL,
                document_loader=custom_document_loader,
                suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
            )
        assert "The messages and signature do not match" in str(context.exception)

    async def test_derive_x_removed_claims(self):
        doc = TEST_LD_DOCUMENT_SIGNED_BBS.copy()
        doc.pop("email")

        with self.assertRaises(Exception) as context:
            await derive(
                document=doc,
                reveal_document=TEST_LD_DOCUMENT_REVEAL_ALL,
                document_loader=custom_document_loader,
                suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
            )
        assert "The messages and signature do not match" in str(context.exception)

    async def test_derive_ld_proofs_reveal_all(self):
        derived = await derive(
            document=TEST_LD_DOCUMENT_SIGNED_BBS,
            reveal_document=TEST_LD_DOCUMENT_REVEAL_ALL,
            document_loader=custom_document_loader,
            suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
        )

        assert derived

    async def test_derive_vc(self):
        derived = await derive_credential(
            credential=TEST_VC_DOCUMENT_SIGNED_BBS,
            reveal_document=TEST_VC_DOCUMENT_REVEAL,
            document_loader=custom_document_loader,
            suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
        )

        assert derived

    async def test_derive_vc_nested(self):
        derived = await derive_credential(
            credential=TEST_VC_DOCUMENT_NESTED_SIGNED_BBS,
            reveal_document=TEST_VC_DOCUMENT_NESTED_REVEAL,
            document_loader=custom_document_loader,
            suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
        )

        assert derived

    async def test_verify_ld_proof(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_PROOF_BBS,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
        )

        assert result.verified

    async def test_verify_derived_ld_proof(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_PROOF_BBS,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
        )

        assert result.verified

    async def test_verify_derived_partial_ld_proof(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_PARTIAL_PROOF_BBS,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
        )

        assert result.verified

    async def test_verify_derived_nested_vc_full_reveal(self):
        result = await verify_credential(
            credential=TEST_VC_DOCUMENT_NESTED_PROOF_BBS,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
        )

        assert result.verified

    async def test_verify_derived_nested_vc_partial_reveal(self):
        result = await verify_credential(
            credential=TEST_VC_DOCUMENT_NESTED_PARTIAL_PROOF_BBS,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
        )

        assert result.verified

    async def test_verify_derived_vc_partial_reveal(self):
        result = await verify_credential(
            credential=TEST_VC_DOCUMENT_PARTIAL_PROOF_BBS,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
        )

        assert result.verified

    async def test_derive_proof_x_invalid_proof_type(self):
        suite = BbsBlsSignatureProof2020(
            key_pair=self.key_pair,
        )

        with self.assertRaises(LinkedDataProofException):
            await suite.derive_proof(
                reveal_document=async_mock.MagicMock(),
                document=async_mock.MagicMock(),
                proof={"type": "incorrect type"},
                document_loader=async_mock.MagicMock(),
            )
