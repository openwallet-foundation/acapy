from asynctest import TestCase


from .....did.did_key import DIDKey
from .....wallet.key_pair import KeyType
from .....wallet.in_memory import InMemoryWallet
from .....core.in_memory import InMemoryProfile
from ....tests.document_loader import custom_document_loader
from ....tests.data import (
    TEST_LD_DOCUMENT,
    TEST_LD_DOCUMENT_SIGNED_ED25519,
    TEST_LD_DOCUMENT_BAD_SIGNED_ED25519,
    TEST_VC_DOCUMENT,
    TEST_VC_DOCUMENT_SIGNED_ED25519,
)
from ...crypto.WalletKeyPair import WalletKeyPair
from ...purposes.AssertionProofPurpose import AssertionProofPurpose

from ...ld_proofs import sign, verify
from ..Ed25519Signature2018 import Ed25519Signature2018


class TestEd25519Signature2018(TestCase):
    test_seed = "testseed000000000000000000000001"

    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.wallet = InMemoryWallet(self.profile)
        self.key = await self.wallet.create_signing_key(
            key_type=KeyType.ED25519, seed=self.test_seed
        )
        self.verification_method = DIDKey.from_public_key_b58(
            self.key.verkey, KeyType.ED25519
        ).key_id

        self.sign_key_pair = WalletKeyPair(
            wallet=self.wallet,
            key_type=KeyType.ED25519,
            public_key_base58=self.key.verkey,
        )
        self.verify_key_pair = WalletKeyPair(
            wallet=self.wallet, key_type=KeyType.ED25519
        )

    async def test_sign_ld_proofs(self):
        signed = await sign(
            document=TEST_LD_DOCUMENT,
            suite=Ed25519Signature2018(
                key_pair=self.sign_key_pair,
                verification_method=self.verification_method,
            ),
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert signed

    async def test_verify_ld_proofs(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_SIGNED_ED25519,
            suites=[Ed25519Signature2018(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert result.verified

    async def test_verify_ld_proofs_not_verified_bad_signature(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_BAD_SIGNED_ED25519,
            suites=[Ed25519Signature2018(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert not result.verified

    async def test_verify_ld_proofs_not_verified_unsigned_statement(self):
        MODIFIED_DOCUMENT = {
            **TEST_LD_DOCUMENT_SIGNED_ED25519,
            "unsigned_claim": "oops",
        }
        result = await verify(
            document=MODIFIED_DOCUMENT,
            suites=[Ed25519Signature2018(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert not result.verified

    async def test_verify_ld_proofs_not_verified_changed_statement(self):
        MODIFIED_DOCUMENT = {
            **TEST_LD_DOCUMENT_SIGNED_ED25519,
            "email": "someOtherEmail@example.com",
        }
        result = await verify(
            document=MODIFIED_DOCUMENT,
            suites=[Ed25519Signature2018(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert not result.verified

    async def test_sign_vc(self):
        signed = await sign(
            document=TEST_VC_DOCUMENT,
            suite=Ed25519Signature2018(
                key_pair=self.sign_key_pair,
                verification_method=self.verification_method,
            ),
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert signed

    async def test_verify_vc(self):
        result = await verify(
            document=TEST_VC_DOCUMENT_SIGNED_ED25519,
            suites=[Ed25519Signature2018(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert result.verified
