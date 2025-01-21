from datetime import datetime
from unittest import IsolatedAsyncioTestCase, mock

import pytest

from ....did.did_key import DIDKey
from ....utils.testing import create_test_profile
from ....wallet.base import BaseWallet
from ....wallet.key_type import ED25519
from ...ld_proofs import (
    Ed25519Signature2018,
    Ed25519Signature2020,
    WalletKeyPair,
)
from ...ld_proofs.error import LinkedDataProofException
from ...tests.document_loader import custom_document_loader
from ...vc_ld import (
    sign_presentation,
    verify_credential,
    verify_presentation,
)
from ...vc_ld import issue_vc as issue
from .test_credential_v2 import (
    CREDENTIAL_V2_ISSUED,
    CREDENTIAL_V2_TEMPLATE,
    CREDENTIAL_V2_VERIFIED,
    PRESENTATION_V2_UNSIGNED,
    PRESENTATION_V2_SIGNED,
)


class TestLinkedDataVerifiableCredential(IsolatedAsyncioTestCase):
    test_seed = "testseed000000000000000000000001"

    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            self.ed25519_key_info = await wallet.create_signing_key(
                key_type=ED25519, seed=self.test_seed
            )
            self.ed25519_verification_method = DIDKey.from_public_key_b58(
                self.ed25519_key_info.verkey, ED25519
            ).key_id

        self.presentation_challenge = "2b1bbff6-e608-4368-bf84-67471b27e41c"

    async def test_v2_issue_Ed25519Signature2020(self):
        suite = Ed25519Signature2020(
            verification_method=self.ed25519_verification_method,
            key_pair=WalletKeyPair(
                profile=self.profile,
                key_type=ED25519,
                public_key_base58=self.ed25519_key_info.verkey,
            ),
            date=datetime.strptime("2019-12-11T03:50:55Z", "%Y-%m-%dT%H:%M:%SZ"),
        )

        issued = await issue(
            credential=CREDENTIAL_V2_TEMPLATE,
            suite=suite,
            document_loader=custom_document_loader,
        )
        assert issued == CREDENTIAL_V2_ISSUED

    async def test_v2_verify_Ed25519Signature2020(self):
        # Verification requires lot less input parameters
        suite = Ed25519Signature2020(
            key_pair=WalletKeyPair(profile=self.profile, key_type=ED25519),
        )
        verified = await verify_credential(
            credential=CREDENTIAL_V2_ISSUED,
            suites=[suite],
            document_loader=custom_document_loader,
        )

        assert verified == CREDENTIAL_V2_VERIFIED

    async def test_verify_presentation(self):
        suite = Ed25519Signature2020(
            key_pair=WalletKeyPair(profile=self.profile, key_type=ED25519),
        )
        verification_result = await verify_presentation(
            presentation=PRESENTATION_V2_UNSIGNED,
            challenge=self.presentation_challenge,
            suites=[suite],
            document_loader=custom_document_loader,
        )

        assert verification_result.verified

    async def test_verify_presentation_x_no_purpose_challenge(self):
        verification_result = await verify_presentation(
            presentation=PRESENTATION_V2_SIGNED,
            suites=[],
            document_loader=custom_document_loader,
        )

        assert not verification_result.verified
        assert 'A "challenge" param is required for AuthenticationProofPurpose' in str(
            verification_result.errors[0]
        )

    async def test_sign_presentation_x_no_purpose_challenge(self):
        with self.assertRaises(LinkedDataProofException) as context:
            await sign_presentation(
                presentation=PRESENTATION_V2_UNSIGNED,
                suite=mock.MagicMock(),
                document_loader=mock.MagicMock(),
            )
        assert 'A "challenge" param is required' in str(context.exception)

    async def test_verify_x_no_proof(self):
        presentation = PRESENTATION_V2_SIGNED.copy()
        presentation.pop("proof")

        verification_result = await verify_presentation(
            presentation=presentation,
            challenge=self.presentation_challenge,
            suites=[],
            document_loader=custom_document_loader,
        )

        assert not verification_result.verified
        assert 'presentation must contain "proof"' in str(verification_result.errors[0])
