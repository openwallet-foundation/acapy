"""Test VcLdpManager."""

from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.core.in_memory.profile import InMemoryProfile
from aries_cloudagent.resolver.default.key import KeyDIDResolver
from aries_cloudagent.resolver.did_resolver import DIDResolver
from aries_cloudagent.vc.ld_proofs.document_loader import DocumentLoader
from aries_cloudagent.vc.ld_proofs.schema_validators.error import VcSchemaValidatorError
from aries_cloudagent.wallet.default_verification_key_strategy import BaseVerificationKeyStrategy, DefaultVerificationKeyStrategy
import pytest
from ....wallet.did_method import  DIDMethods
from ..manager import VcLdpManager, VcLdpManagerError
from ..models.credential import VerifiableCredential
from ..models.options import LDProofVCOptions
from ...tests.data import (
    TEST_LD_DOCUMENT_CORRECT_SCHEMA,
    TEST_LD_DOCUMENT_INCORRECT_SCHEMA,
    TEST_LD_DOCUMENT_INCORRECT_URL
)

TEST_DID_SOV = "did:sov:LjgpST2rjsoxYegQDRm7EL"
TEST_DID_KEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
TEST_UUID = "urn:uuid:1b6824b1-db3f-43e8-8f17-baf618743635"



class TestCredentialSchema(IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.did_resolver = DIDResolver([KeyDIDResolver()])
        self.profile = InMemoryProfile.test_profile(
        {},
        {
            DIDMethods: DIDMethods(),
            BaseVerificationKeyStrategy: DefaultVerificationKeyStrategy(),
            DIDResolver: self.did_resolver,
        },
    )
        self.ldp_manager = VcLdpManager(self.profile)
        self.profile.context.injector.bind_instance(DocumentLoader, DocumentLoader(self.profile))
        self.options = LDProofVCOptions.deserialize({
            "proofType": "Ed25519Signature2018",
            "created": "2019-12-11T03:50:55",
        })
        

    async def test_derive_ld_proofs(self):
        vc = VerifiableCredential.deserialize(TEST_LD_DOCUMENT_CORRECT_SCHEMA)
        detail = await self.ldp_manager.prepare_credential(vc, self.options)
        assert detail

    async def test_prepare_detail(
        self
    ):
        vc = VerifiableCredential.deserialize(TEST_LD_DOCUMENT_CORRECT_SCHEMA)
        detail = await self.ldp_manager.prepare_credential(vc, self.options)
        assert detail

    
    async def test_prepare_detail_fail(
        self
    ):
        vc = VerifiableCredential.deserialize(TEST_LD_DOCUMENT_INCORRECT_SCHEMA)
        with pytest.raises(VcLdpManagerError) as ldp_manager_error:
            with pytest.raises(VcSchemaValidatorError) as validator_error:
                await self.ldp_manager.prepare_credential(vc, self.options)
    
            assert '''"reason": "\'2.1\' is not of type \'number\'", "json_path": "$.credentialSubject.creditsEarned"''' in validator_error.value.args[0]
        assert ldp_manager_error.value.args[0] == 'credentialSchema validation error'

    async def test_prepare_detail_invalid_url(
        self
    ):
        vc = VerifiableCredential.deserialize(TEST_LD_DOCUMENT_INCORRECT_URL)

        with pytest.raises(VcLdpManagerError) as ldp_manager_error:
            with pytest.raises(VcSchemaValidatorError) as validator_error:
                await self.ldp_manager.prepare_credential(vc, self.options)

            assert '''The HTTP scheme MUST be "https" for http://purl.imsglobal.org/spec/ob/v3p0/schema/json-ld/ob_v3p0_anyachievementcredential_schema.json''' in validator_error.value.args[0]
        assert ldp_manager_error.value.args[0] == 'credentialSchema validation error'