from asynctest import TestCase, mock as async_mock
import pytest

from aries_cloudagent.wallet.key_type import BLS12381G2

from .....did.did_key import DIDKey
from .....wallet.key_pair import KeyType
from .....wallet.in_memory import InMemoryWallet
from .....core.in_memory import InMemoryProfile
from ....tests.document_loader import custom_document_loader
from ....tests.data import (
    TEST_LD_DOCUMENT,
    TEST_LD_DOCUMENT_SIGNED_BBS,
    TEST_LD_DOCUMENT_BAD_SIGNED_BBS,
    TEST_VC_DOCUMENT,
    TEST_VC_DOCUMENT_SIGNED_BBS,
)

from ...error import LinkedDataProofException
from ...crypto.wallet_key_pair import WalletKeyPair
from ...purposes.assertion_proof_purpose import AssertionProofPurpose
from ...ld_proofs import sign, verify

from ..bbs_bls_signature_2020 import BbsBlsSignature2020


@pytest.mark.ursa_bbs_signatures
class TestBbsBlsSignature2020(TestCase):
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

        self.sign_key_pair = WalletKeyPair(
            wallet=self.wallet,
            key_type=BLS12381G2,
            public_key_base58=self.key.verkey,
        )
        self.verify_key_pair = WalletKeyPair(wallet=self.wallet, key_type=BLS12381G2)

    async def test_sign_ld_proofs(self):
        signed = await sign(
            document=TEST_LD_DOCUMENT,
            suite=BbsBlsSignature2020(
                key_pair=self.sign_key_pair,
                verification_method=self.verification_method,
            ),
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert signed

    async def test_verify_ld_proofs(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_SIGNED_BBS,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert result.verified

    async def test_verify_ld_proofs_not_verified_bad_signature(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_BAD_SIGNED_BBS,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert not result.verified

    async def test_verify_ld_proofs_not_verified_unsigned_statement(self):
        MODIFIED_DOCUMENT = {**TEST_LD_DOCUMENT_SIGNED_BBS, "unsigned_claim": "oops"}
        result = await verify(
            document=MODIFIED_DOCUMENT,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert not result.verified

    async def test_verify_ld_proofs_not_verified_changed_statement(self):
        MODIFIED_DOCUMENT = {
            **TEST_LD_DOCUMENT_SIGNED_BBS,
            "email": "someOtherEmail@example.com",
        }
        result = await verify(
            document=MODIFIED_DOCUMENT,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert not result.verified

    async def test_sign_vc(self):
        signed = await sign(
            document=TEST_VC_DOCUMENT,
            suite=BbsBlsSignature2020(
                key_pair=self.sign_key_pair,
                verification_method=self.verification_method,
            ),
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert signed

    async def test_verify_vc(self):
        result = await verify(
            document=TEST_VC_DOCUMENT_SIGNED_BBS,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert result.verified

    async def test_verify_signature_x_invalid_proof_value(self):
        suite = BbsBlsSignature2020(
            key_pair=self.sign_key_pair,
            verification_method=self.verification_method,
        )

        with self.assertRaises(LinkedDataProofException):
            await suite.verify_signature(
                verify_data=async_mock.MagicMock(),
                verification_method=async_mock.MagicMock(),
                document=async_mock.MagicMock(),
                proof={"proofValue": {"not": "a string"}},
                document_loader=async_mock.MagicMock(),
            )
