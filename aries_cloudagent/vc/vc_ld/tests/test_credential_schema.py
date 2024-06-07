"""Test VcLdpManager."""

from jsonschema import ValidationError
from aries_cloudagent.core.in_memory.profile import InMemoryProfile
from aries_cloudagent.resolver.default.key import KeyDIDResolver
from aries_cloudagent.resolver.did_resolver import DIDResolver
from aries_cloudagent.vc.ld_proofs.document_loader import DocumentLoader
from aries_cloudagent.vc.tests.data.test_ld_document_correct_schema import TEST_LD_DOCUMENT_CORRECT_SCHEMA
from aries_cloudagent.vc.tests.data.test_ld_document_incorrect_schema import TEST_LD_DOCUMENT_INCORRECT_SCHEMA
from aries_cloudagent.wallet.default_verification_key_strategy import BaseVerificationKeyStrategy, DefaultVerificationKeyStrategy
import pytest


from ....core.profile import Profile
from ....wallet.base import BaseWallet
from ....storage.vc_holder.base import VCHolder
from ....wallet.did_method import KEY, DIDMethods
from ....wallet.key_type import ED25519
from ...ld_proofs.suites.bbs_bls_signature_2020 import BbsBlsSignature2020
from ...ld_proofs.suites.ed25519_signature_2018 import Ed25519Signature2018
from ..manager import VcLdpManager
from ..models.credential import VerifiableCredential
from ..models.options import LDProofVCOptions

TEST_DID_SOV = "did:sov:LjgpST2rjsoxYegQDRm7EL"
TEST_DID_KEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
TEST_UUID = "urn:uuid:1b6824b1-db3f-43e8-8f17-baf618743635"


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


@pytest.mark.asyncio
async def test_prepare_detail(
    manager: VcLdpManager,
):
    options  =  LDProofVCOptions.deserialize({
        "proofType": "Ed25519Signature2018",
        "created": "2019-12-11T03:50:55",
    })

    vc = VerifiableCredential.deserialize(TEST_LD_DOCUMENT_CORRECT_SCHEMA)

    detail = await manager.prepare_credential(vc, options, None, True)

    assert detail

@pytest.mark.asyncio
async def test_prepare_detail_fail(
    manager: VcLdpManager,
):
    options = LDProofVCOptions.deserialize({
        "proofType": "Ed25519Signature2018",
        "created": "2019-12-11T03:50:55",
    })
    options.proof_type = BbsBlsSignature2020.signature_type

    vc = VerifiableCredential.deserialize(TEST_LD_DOCUMENT_INCORRECT_SCHEMA)

    # TODO: Fix this test
    with pytest.raises(ValidationError) as context:
        await manager.prepare_credential(vc, options, None, True)
        assert "'issuanceDate': ['Missing data for required field.']" in str(
            context.value)
    


@pytest.mark.asyncio(scope="module")
async def test_store(
    profile: Profile,
    manager: VcLdpManager,
):
    options  =  LDProofVCOptions.deserialize({
        "proofType": "Ed25519Signature2018",
        "created": "2019-12-11T03:50:55",
    })

    vc = VerifiableCredential.deserialize(TEST_LD_DOCUMENT_CORRECT_SCHEMA)
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
    assert record.schema_ids.pop() == TEST_LD_DOCUMENT_CORRECT_SCHEMA.get('credentialSchema')[0].get('id')
