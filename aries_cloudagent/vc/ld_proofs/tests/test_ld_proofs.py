from asynctest import TestCase
import traceback

from datetime import datetime

from ....wallet.base import KeyInfo
from ....wallet.crypto import KeyType
from ....did.did_key import DIDKey
from ....wallet.in_memory import InMemoryWallet
from ....core.in_memory import InMemoryProfile
from ...ld_proofs import (
    sign,
    Ed25519Signature2018,
    Ed25519WalletKeyPair,
    AssertionProofPurpose,
    verify,
)
from ...tests.document_loader import custom_document_loader
from .test_doc import DOC_TEMPLATE, DOC_SIGNED, DOC_VERIFIED


class TestLDProofs(TestCase):
    test_seed = "testseed000000000000000000000001"
    key_info: KeyInfo = None

    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.wallet = InMemoryWallet(self.profile)
        self.key_info = await self.wallet.create_signing_key(self.test_seed)
        self.verification_method = DIDKey.from_public_key_b58(
            self.key_info.verkey, KeyType.ED25519
        ).key_id

    async def test_sign(self):
        # Use different key pair and suite for signing and verification
        # as during verification a lot of information can be extracted
        # from the proof / document
        suite = Ed25519Signature2018(
            verification_method=self.verification_method,
            key_pair=Ed25519WalletKeyPair(
                wallet=self.wallet, public_key_base58=self.key_info.verkey
            ),
            date=datetime.strptime("2019-12-11T03:50:55Z", "%Y-%m-%dT%H:%M:%SZ"),
        )
        signed = await sign(
            document=DOC_TEMPLATE,
            suite=suite,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert DOC_SIGNED == signed

    async def test_verify(self):
        # Verification requires lot less input parameters
        suite = Ed25519Signature2018(
            key_pair=Ed25519WalletKeyPair(wallet=self.wallet),
        )

        result = await verify(
            document=DOC_SIGNED,
            suites=[suite],
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        if not result.verified:
            raise result.errors[0]

        assert DOC_VERIFIED == result
