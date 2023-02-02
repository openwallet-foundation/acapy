from asynctest import TestCase, mock as async_mock
from datetime import datetime

import pytest

from ....wallet.key_type import BLS12381G2, ED25519
from ....did.did_key import DIDKey
from ....wallet.in_memory import InMemoryWallet
from ....core.in_memory import InMemoryProfile
from ...ld_proofs import Ed25519Signature2018, WalletKeyPair, BbsBlsSignature2020
from ...vc_ld import (
    issue_vc as issue,
    verify_credential,
    create_presentation,
    sign_presentation,
    verify_presentation,
    derive_credential,
)
from ...ld_proofs.error import LinkedDataProofException
from ...tests.document_loader import custom_document_loader
from .test_credential import (
    CREDENTIAL_TEMPLATE,
    CREDENTIAL_ISSUED,
    CREDENTIAL_VERIFIED,
    PRESENTATION_SIGNED,
    PRESENTATION_UNSIGNED,
    CREDENTIAL_TEMPLATE_BBS,
    CREDENTIAL_ISSUED_BBS,
)


class TestLinkedDataVerifiableCredential(TestCase):
    test_seed = "testseed000000000000000000000001"

    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.wallet = InMemoryWallet(self.profile)

        self.ed25519_key_info = await self.wallet.create_signing_key(
            key_type=ED25519, seed=self.test_seed
        )
        self.ed25519_verification_method = DIDKey.from_public_key_b58(
            self.ed25519_key_info.verkey, ED25519
        ).key_id

        self.bls12381g2_key_info = await self.wallet.create_signing_key(
            key_type=BLS12381G2, seed=self.test_seed
        )

        self.bls12381g2_verification_method = DIDKey.from_public_key_b58(
            self.bls12381g2_key_info.verkey, BLS12381G2
        ).key_id

        self.presentation_challenge = "2b1bbff6-e608-4368-bf84-67471b27e41c"

    async def test_issue_Ed25519Signature2018(self):
        # Use different key pair and suite for signing and verification
        # as during verification a lot of information can be extracted
        # from the proof / document
        suite = Ed25519Signature2018(
            verification_method=self.ed25519_verification_method,
            key_pair=WalletKeyPair(
                wallet=self.wallet,
                key_type=ED25519,
                public_key_base58=self.ed25519_key_info.verkey,
            ),
            date=datetime.strptime("2019-12-11T03:50:55Z", "%Y-%m-%dT%H:%M:%SZ"),
        )

        issued = await issue(
            credential=CREDENTIAL_TEMPLATE,
            suite=suite,
            document_loader=custom_document_loader,
        )

        assert issued == CREDENTIAL_ISSUED

    async def test_issue_x_invalid_credential_structure(self):
        credential = CREDENTIAL_TEMPLATE.copy()
        credential.pop("issuer")

        with self.assertRaises(LinkedDataProofException) as context:
            await issue(
                credential=credential,
                suite=async_mock.MagicMock(),
                document_loader=async_mock.MagicMock(),
            )
        assert "invalid structure" in str(context.exception)

    async def test_derive_x_invalid_credential_structure(self):
        credential = CREDENTIAL_TEMPLATE.copy()
        credential.pop("issuer")

        with self.assertRaises(LinkedDataProofException) as context:
            await derive_credential(
                credential=credential,
                reveal_document=async_mock.MagicMock(),
                suite=async_mock.MagicMock(),
                document_loader=async_mock.MagicMock(),
            )
        assert "invalid structure" in str(context.exception)

    async def test_verify_Ed25519Signature2018(self):
        # Verification requires lot less input parameters
        suite = Ed25519Signature2018(
            key_pair=WalletKeyPair(wallet=self.wallet, key_type=ED25519),
        )
        verified = await verify_credential(
            credential=CREDENTIAL_ISSUED,
            suites=[suite],
            document_loader=custom_document_loader,
        )

        assert verified == CREDENTIAL_VERIFIED

    async def test_verify_x_invalid_credential_structure(self):
        credential = CREDENTIAL_ISSUED.copy()
        credential.pop("issuer")

        result = await verify_credential(
            credential=credential,
            suites=[],
            document_loader=async_mock.MagicMock(),
        )

        assert not result.verified
        assert "invalid structure" in str(result.errors[0])

    @pytest.mark.ursa_bbs_signatures
    async def test_issue_BbsBlsSignature2020(self):
        # Use different key pair and suite for signing and verification
        # as during verification a lot of information can be extracted
        # from the proof / document
        suite = BbsBlsSignature2020(
            verification_method=self.bls12381g2_verification_method,
            key_pair=WalletKeyPair(
                wallet=self.wallet,
                key_type=BLS12381G2,
                public_key_base58=self.bls12381g2_key_info.verkey,
            ),
            date=datetime.strptime("2019-12-11T03:50:55Z", "%Y-%m-%dT%H:%M:%SZ"),
        )

        issued = await issue(
            credential=CREDENTIAL_TEMPLATE_BBS,
            suite=suite,
            document_loader=custom_document_loader,
        )

        assert issued

        result = await verify_credential(
            credential=issued, suites=[suite], document_loader=custom_document_loader
        )

        assert result.verified

    async def test_verify_BbsBlsSignature2020(self):
        # Verification requires lot less input parameters
        suite = BbsBlsSignature2020(
            key_pair=WalletKeyPair(wallet=self.wallet, key_type=BLS12381G2),
        )
        result = await verify_credential(
            credential=CREDENTIAL_ISSUED_BBS,
            suites=[suite],
            document_loader=custom_document_loader,
        )

        assert result.verified

    async def test_create_presentation(self):
        credential = CREDENTIAL_ISSUED.copy()
        credential.pop("issuer")

        with self.assertRaises(LinkedDataProofException) as context:
            await create_presentation(credentials=[credential])
        assert "Not all credentials have a valid structure" in str(context.exception)

    async def test_create_presentation_x_invalid_credential_structures(self):
        unsigned_presentation = await create_presentation(
            credentials=[CREDENTIAL_ISSUED]
        )

        suite = Ed25519Signature2018(
            verification_method=self.ed25519_verification_method,
            key_pair=WalletKeyPair(
                wallet=self.wallet,
                key_type=ED25519,
                public_key_base58=self.ed25519_key_info.verkey,
            ),
            date=datetime.strptime("2020-12-11T03:50:55Z", "%Y-%m-%dT%H:%M:%SZ"),
        )

        assert unsigned_presentation == PRESENTATION_UNSIGNED

        presentation = await sign_presentation(
            presentation=unsigned_presentation,
            suite=suite,
            document_loader=custom_document_loader,
            challenge=self.presentation_challenge,
        )

        assert presentation == PRESENTATION_SIGNED

        # test id property
        assert "id" in await create_presentation(
            credentials=[CREDENTIAL_ISSUED],
            presentation_id="https://presentation_id.com",
        )

    @pytest.mark.ursa_bbs_signatures
    async def test_sign_presentation_bbsbls(self):
        unsigned_presentation = await create_presentation(
            credentials=[CREDENTIAL_ISSUED]
        )

        suite = BbsBlsSignature2020(
            verification_method=self.bls12381g2_verification_method,
            key_pair=WalletKeyPair(
                wallet=self.wallet,
                key_type=BLS12381G2,
                public_key_base58=self.bls12381g2_key_info.verkey,
            ),
            date=datetime.strptime("2020-12-11T03:50:55Z", "%Y-%m-%dT%H:%M:%SZ"),
        )

        assert unsigned_presentation == PRESENTATION_UNSIGNED
        unsigned_presentation["@context"].append("https://w3id.org/security/bbs/v1")
        presentation = await sign_presentation(
            presentation=unsigned_presentation,
            suite=suite,
            document_loader=custom_document_loader,
            challenge=self.presentation_challenge,
        )

    async def test_verify_presentation(self):
        suite = Ed25519Signature2018(
            key_pair=WalletKeyPair(wallet=self.wallet, key_type=ED25519),
        )
        verification_result = await verify_presentation(
            presentation=PRESENTATION_SIGNED,
            challenge=self.presentation_challenge,
            suites=[suite],
            document_loader=custom_document_loader,
        )

        assert verification_result.verified

    async def test_verify_presentation_x_no_purpose_challenge(self):
        verification_result = await verify_presentation(
            presentation=PRESENTATION_SIGNED,
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
                presentation=PRESENTATION_UNSIGNED,
                suite=async_mock.MagicMock(),
                document_loader=async_mock.MagicMock(),
            )
        assert 'A "challenge" param is required' in str(context.exception)

    async def test_verify_x_no_proof(self):
        presentation = PRESENTATION_SIGNED.copy()
        presentation.pop("proof")

        verification_result = await verify_presentation(
            presentation=presentation,
            challenge=self.presentation_challenge,
            suites=[],
            document_loader=custom_document_loader,
        )

        assert not verification_result.verified
        assert 'presentation must contain "proof"' in str(verification_result.errors[0])
