"""Test VcLdpManager."""

import pytest

from aries_cloudagent.tests import mock

from ....core.in_memory.profile import InMemoryProfile
from ....core.profile import Profile
from ....did.did_key import DIDKey
from ....resolver.default.key import KeyDIDResolver
from ....resolver.did_resolver import DIDResolver
from ....wallet.base import BaseWallet
from ....storage.vc_holder.base import VCHolder
from ....wallet.default_verification_key_strategy import (
    BaseVerificationKeyStrategy,
    DefaultVerificationKeyStrategy,
)
from ....wallet.did_info import DIDInfo
from ....wallet.did_method import DIDMethod, DIDMethods, KEY, SOV
from ....wallet.error import WalletNotFoundError
from ....wallet.key_type import BLS12381G2, ED25519
from ...ld_proofs.constants import (
    SECURITY_CONTEXT_BBS_URL,
    SECURITY_CONTEXT_ED25519_2020_URL,
)
from ...ld_proofs.crypto.wallet_key_pair import WalletKeyPair
from ...ld_proofs.document_loader import DocumentLoader
from ...ld_proofs.purposes.authentication_proof_purpose import (
    AuthenticationProofPurpose,
)
from ...ld_proofs.purposes.credential_issuance_purpose import CredentialIssuancePurpose
from ...ld_proofs.suites.bbs_bls_signature_2020 import BbsBlsSignature2020
from ...ld_proofs.suites.bbs_bls_signature_proof_2020 import BbsBlsSignatureProof2020
from ...ld_proofs.suites.ed25519_signature_2018 import Ed25519Signature2018
from ...ld_proofs.suites.ed25519_signature_2020 import Ed25519Signature2020
from ..manager import VcLdpManager, VcLdpManagerError
from ..models.credential import VerifiableCredential
from ..models.options import LDProofVCOptions

TEST_DID_SOV = "did:sov:LjgpST2rjsoxYegQDRm7EL"
TEST_DID_KEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
TEST_UUID = "urn:uuid:dc86e95c-dc85-4f91-b563-82657d095c44"
VC = {
    "credential": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
            {
                "ex": "https://example.org/test#",
                "test": "ex:test",
            },
        ],
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "credentialSubject": {"test": "key"},
        "issuanceDate": "2021-04-12",
        "issuer": TEST_DID_KEY,
    },
    "options": {
        "proofType": "Ed25519Signature2018",
        "created": "2019-12-11T03:50:55",
    },
}


@pytest.fixture
def resolver():
    yield DIDResolver([KeyDIDResolver()])


@pytest.fixture
def profile(resolver: DIDResolver):
    profile = InMemoryProfile.test_profile(
        {},
        {
            DIDMethods: DIDMethods(),
            BaseVerificationKeyStrategy: DefaultVerificationKeyStrategy(),
            DIDResolver: resolver,
        },
    )
    profile.context.injector.bind_instance(DocumentLoader, DocumentLoader(profile))
    yield profile


@pytest.fixture
def manager(profile: Profile):
    yield VcLdpManager(profile)


@pytest.fixture
def vc():
    yield VerifiableCredential.deserialize(VC["credential"])


@pytest.fixture
def options():
    yield LDProofVCOptions.deserialize(VC["options"])


@pytest.mark.asyncio
async def test_assert_can_issue_with_id_and_proof_type(manager: VcLdpManager):
    with pytest.raises(VcLdpManagerError) as context:
        await manager.assert_can_issue_with_id_and_proof_type(
            "issuer_id", "random_proof_type"
        )

        assert (
            "Unable to sign credential with unsupported proof type random_proof_type"
            in str(context.value)
        )

    with pytest.raises(VcLdpManagerError) as context:
        await manager.assert_can_issue_with_id_and_proof_type(
            "not_did", Ed25519Signature2018.signature_type
        )
        assert "Unable to issue credential with issuer id: not_did" in str(
            context.value
        )

    with mock.patch.object(
        manager,
        "_did_info_for_did",
        mock.CoroutineMock(),
    ) as mock_did_info:
        did_info = DIDInfo(
            did=TEST_DID_SOV,
            verkey="verkey",
            metadata={},
            method=SOV,
            key_type=ED25519,
        )
        mock_did_info.return_value = did_info
        await manager.assert_can_issue_with_id_and_proof_type(
            "did:key:found", Ed25519Signature2018.signature_type
        )
        await manager.assert_can_issue_with_id_and_proof_type(
            "did:key:found", Ed25519Signature2020.signature_type
        )

        invalid_did_info = DIDInfo(
            did=TEST_DID_SOV,
            verkey="verkey",
            metadata={},
            method=SOV,
            key_type=BLS12381G2,
        )
        mock_did_info.return_value = invalid_did_info
        with pytest.raises(VcLdpManagerError) as context:
            await manager.assert_can_issue_with_id_and_proof_type(
                "did:key:found", Ed25519Signature2018.signature_type
            )
            assert "Unable to issue credential with issuer id" in str(context.value)

        mock_did_info.side_effect = (WalletNotFoundError,)
        with pytest.raises(VcLdpManagerError) as context:
            await manager.assert_can_issue_with_id_and_proof_type(
                "did:key:notfound", Ed25519Signature2018.signature_type
            )
            assert "Issuer did did:key:notfound not found" in str(context.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("method", [SOV, KEY])
async def test_get_did_info_for_did_sov(
    method: DIDMethod, profile: Profile, manager: VcLdpManager
):
    async with profile.session() as session:
        wallet = session.inject(BaseWallet)
        did = await wallet.create_local_did(
            method=method,
            key_type=ED25519,
        )
    did_info = await manager._did_info_for_did(did.did)
    assert did_info == did


@pytest.mark.asyncio
async def test_get_suite_for_document(manager: VcLdpManager):
    vc = VerifiableCredential.deserialize(VC["credential"])
    options = LDProofVCOptions.deserialize(VC["options"])

    with mock.patch.object(
        manager,
        "assert_can_issue_with_id_and_proof_type",
        mock.CoroutineMock(),
    ) as mock_can_issue, mock.patch.object(
        manager,
        "_did_info_for_did",
        mock.CoroutineMock(),
    ) as mock_did_info:
        suite = await manager._get_suite_for_document(vc, options)

        assert suite.signature_type == options.proof_type
        assert isinstance(suite, Ed25519Signature2018)
        assert suite.verification_method == DIDKey.from_did(TEST_DID_KEY).key_id
        assert suite.proof == {"created": VC["options"]["created"]}
        assert isinstance(suite.key_pair, WalletKeyPair)
        assert suite.key_pair.key_type == ED25519
        assert suite.key_pair.public_key_base58 == mock_did_info.return_value.verkey

        mock_can_issue.assert_called_once_with(vc.issuer_id, options.proof_type)
        mock_did_info.assert_called_once_with(vc.issuer_id)


@pytest.mark.asyncio
async def test_get_suite(manager: VcLdpManager):
    proof = mock.MagicMock()
    did_info = mock.MagicMock()

    suite = await manager._get_suite(
        proof_type=BbsBlsSignature2020.signature_type,
        verification_method="verification_method",
        proof=proof,
        did_info=did_info,
    )

    assert isinstance(suite, BbsBlsSignature2020)
    assert suite.verification_method == "verification_method"
    assert suite.proof == proof
    assert isinstance(suite.key_pair, WalletKeyPair)
    assert suite.key_pair.key_type == BLS12381G2
    assert suite.key_pair.public_key_base58 == did_info.verkey

    suite = await manager._get_suite(
        proof_type=Ed25519Signature2018.signature_type,
        verification_method="verification_method",
        proof=proof,
        did_info=did_info,
    )

    assert isinstance(suite, Ed25519Signature2018)
    assert suite.verification_method == "verification_method"
    assert suite.proof == proof
    assert isinstance(suite.key_pair, WalletKeyPair)
    assert suite.key_pair.key_type == ED25519
    assert suite.key_pair.public_key_base58 == did_info.verkey

    suite = await manager._get_suite(
        proof_type=Ed25519Signature2020.signature_type,
        verification_method="verification_method",
        proof=proof,
        did_info=did_info,
    )

    assert isinstance(suite, Ed25519Signature2020)
    assert suite.verification_method == "verification_method"
    assert suite.proof == proof
    assert isinstance(suite.key_pair, WalletKeyPair)
    assert suite.key_pair.key_type == ED25519
    assert suite.key_pair.public_key_base58 == did_info.verkey


@pytest.mark.asyncio
async def test_get_proof_purpose(manager: VcLdpManager):
    purpose = manager._get_proof_purpose()
    assert isinstance(purpose, CredentialIssuancePurpose)

    purpose = manager._get_proof_purpose(
        proof_purpose=AuthenticationProofPurpose.term,
        challenge="challenge",
        domain="domain",
    )
    assert isinstance(purpose, AuthenticationProofPurpose)
    assert purpose.domain == "domain"
    assert purpose.challenge == "challenge"

    with pytest.raises(VcLdpManagerError) as context:
        manager._get_proof_purpose(proof_purpose=AuthenticationProofPurpose.term)
    assert "Challenge is required for" in str(context.value)

    with pytest.raises(VcLdpManagerError) as context:
        manager._get_proof_purpose(proof_purpose="random")
    assert "Unsupported proof purpose: random" in str(context.value)


@pytest.mark.asyncio
async def test_prepare_detail(
    manager: VcLdpManager, vc: VerifiableCredential, options: LDProofVCOptions
):
    options.proof_type = BbsBlsSignature2020.signature_type

    assert SECURITY_CONTEXT_BBS_URL not in vc.context_urls

    detail = await manager.prepare_credential(vc, options)

    assert SECURITY_CONTEXT_BBS_URL in vc.context_urls


@pytest.mark.asyncio
async def test_prepare_detail_ed25519_2020(
    manager: VcLdpManager, vc: VerifiableCredential, options: LDProofVCOptions
):
    options.proof_type = Ed25519Signature2020.signature_type

    assert SECURITY_CONTEXT_ED25519_2020_URL not in vc.context_urls

    detail = await manager.prepare_credential(vc, options)

    assert SECURITY_CONTEXT_ED25519_2020_URL in vc.context_urls


@pytest.mark.asyncio(scope="module")
async def test_issue(
    profile: Profile,
    manager: VcLdpManager,
    vc: VerifiableCredential,
    options: LDProofVCOptions,
):
    async with profile.session() as session:
        wallet = session.inject(BaseWallet)
        did = await wallet.create_local_did(
            method=KEY,
            key_type=ED25519,
        )
    vc.issuer = did.did
    options.proof_type = Ed25519Signature2018.signature_type
    cred = await manager.issue(vc, options)
    assert cred


@pytest.mark.asyncio(scope="module")
async def test_issue_ed25519_2020(
    profile: Profile,
    manager: VcLdpManager,
    vc: VerifiableCredential,
    options: LDProofVCOptions,
):
    """Ensure ed25519 2020 context added to issued cred."""
    async with profile.session() as session:
        wallet = session.inject(BaseWallet)
        did = await wallet.create_local_did(
            method=KEY,
            key_type=ED25519,
        )
    vc.issuer = did.did
    options.proof_type = Ed25519Signature2020.signature_type
    cred = await manager.issue(vc, options)
    assert cred


@pytest.mark.asyncio(scope="module")
@pytest.mark.ursa_bbs_signatures
async def test_issue_bbs(
    profile: Profile,
    manager: VcLdpManager,
    vc: VerifiableCredential,
    options: LDProofVCOptions,
):
    """Ensure BBS context is added to issued cred."""
    async with profile.session() as session:
        wallet = session.inject(BaseWallet)
        did = await wallet.create_local_did(
            method=KEY,
            key_type=BLS12381G2,
        )
    vc.issuer = did.did
    options.proof_type = BbsBlsSignature2020.signature_type
    cred = await manager.issue(vc, options)
    assert cred


@pytest.mark.asyncio
async def test_get_all_suites(manager: VcLdpManager):
    suites = await manager._get_all_proof_suites()
    assert len(suites) == 4
    types = (
        Ed25519Signature2018,
        Ed25519Signature2020,
        BbsBlsSignature2020,
        BbsBlsSignatureProof2020,
    )
    for suite in suites:
        assert isinstance(suite, types)


@pytest.mark.asyncio(scope="module")
async def test_store(
    profile: Profile,
    manager: VcLdpManager,
    vc: VerifiableCredential,
    options: LDProofVCOptions,
):
    async with profile.session() as session:
        wallet = session.inject(BaseWallet)
        did = await wallet.create_local_did(
            method=KEY,
            key_type=ED25519,
        )
    vc.issuer = did.did
    options.proof_type = Ed25519Signature2018.signature_type
    cred = await manager.issue(vc, options)
    await manager.store_credential(cred, options, TEST_UUID)
    async with profile.session() as session:
        holder = session.inject(VCHolder)
        record = await holder.retrieve_credential_by_id(record_id=TEST_UUID)
    assert record
