from asynctest import TestCase

from datetime import datetime

from ....wallet.base import KeyInfo
from ....wallet.util import naked_to_did_key
from ....wallet.in_memory import InMemoryWallet
from ....core.in_memory import InMemoryProfile
from ...ld_proofs import (
    Ed25519Signature2018,
    Ed25519WalletKeyPair,
    CredentialIssuancePurpose,
    AssertionProofPurpose,
)
from ...vc_ld import issue, verify_credential
from ...tests.document_loader import custom_document_loader
from .test_credential import CREDENTIAL_TEMPLATE, CREDENTIAL_ISSUED, CREDENTIAL_VERIFIED


class TestLinkedDataVerifiableCredential(TestCase):
    test_seed = "testseed000000000000000000000001"
    key_info: KeyInfo = None

    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.wallet = InMemoryWallet(self.profile)
        self.key_info = await self.wallet.create_signing_key(self.test_seed)

        self.key_pair = Ed25519WalletKeyPair(
            wallet=self.wallet, public_key_base58=self.key_info.verkey
        )
        self.verification_method = (
            naked_to_did_key(self.key_info.verkey) + "#" + self.key_pair.fingerprint()
        )
        self.suite = Ed25519Signature2018(
            # TODO: should we provide verification_method here? Or abstract?
            verification_method=self.verification_method,
            key_pair=Ed25519WalletKeyPair(
                wallet=self.wallet, public_key_base58=self.key_info.verkey
            ),
            date=datetime.strptime("2019-12-11T03:50:55Z", "%Y-%m-%dT%H:%M:%SZ"),
        )

    async def test_issue(self):
        issued = await issue(
            credential=CREDENTIAL_TEMPLATE,
            suite=self.suite,
            purpose=CredentialIssuancePurpose(),
            document_loader=custom_document_loader,
        )

        assert issued == CREDENTIAL_ISSUED

    async def test_verify(self):
        verified = await verify_credential(
            credential=CREDENTIAL_ISSUED,
            suite=self.suite,
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert verified == CREDENTIAL_VERIFIED
