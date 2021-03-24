from unittest import mock

from asynctest import TestCase as AsyncTestCase
from pydid import DIDDocument, VerificationSuite

from ......core.in_memory import InMemoryProfile
from ......messaging.decorators.attach_decorator import AttachDecorator
from .....didcomm_prefix import DIDCommPrefix
from ...message_types import DIDX_RESPONSE
from ..response import DIDXResponse


class TestConfig:
    test_seed = "testseed000000000000000000000001"
    test_did = "did:sov:55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"

    def make_did_doc(self):
        did = self.test_did
        verkey = self.test_verkey
        endpoint = self.test_endpoint
        builder = DIDDocumentBuilder(did)
        vmethod = builder.verification_methods.add(
            ident="1",
            suite=VerificationSuite("Ed25519VerificationKey2018", "publicKeyBase58"),
            material=verkey,
        )
        builder.services.add_didcomm(
            endpoint=endpoint,
            type_="IndyAgent",
            recipient_keys=[vmethod],
            routing_keys=[],
        )

        return builder.build()


class TestDIDXResponse(AsyncTestCase, TestConfig):
    async def setUp(self):
        self.wallet = InMemoryProfile.test_session().wallet
        self.did_info = await self.wallet.create_local_did()

        did_doc_attach = AttachDecorator.from_indy_dict(self.make_did_doc().serialize())
        await did_doc_attach.data.sign(self.did_info.verkey, self.wallet)

        self.response = DIDXResponse(
            did=TestConfig.test_did,
            did_doc_attach=did_doc_attach,
        )

    def test_init(self):
        """Test initialization."""
        assert self.response.did == TestConfig.test_did

    def test_type(self):
        assert self.response._type == DIDCommPrefix.qualify_current(DIDX_RESPONSE)

    @mock.patch(
        "aries_cloudagent.protocols.didexchange.v1_0.messages."
        "response.DIDXResponseSchema.load"
    )
    def test_deserialize(self, mock_response_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        response = DIDXResponse.deserialize(obj)
        mock_response_schema_load.assert_called_once_with(obj)

        assert response is mock_response_schema_load.return_value

    @mock.patch(
        "aries_cloudagent.protocols.didexchange.v1_0.messages."
        "response.DIDXResponseSchema.dump"
    )
    def test_serialize(self, mock_response_schema_dump):
        """
        Test serialization.
        """
        response_dict = self.response.serialize()
        mock_response_schema_dump.assert_called_once_with(self.response)

        assert response_dict is mock_response_schema_dump.return_value


class TestDIDXResponseSchema(AsyncTestCase, TestConfig):
    """Test response schema."""

    async def setUp(self):
        self.wallet = InMemoryProfile.test_session().wallet
        self.did_info = await self.wallet.create_local_did()

        did_doc_attach = AttachDecorator.from_indy_dict(self.make_did_doc().serialize())
        await did_doc_attach.data.sign(self.did_info.verkey, self.wallet)

        self.response = DIDXResponse(
            did=TestConfig.test_did,
            did_doc_attach=did_doc_attach,
        )

    async def test_make_model(self):
        data = self.response.serialize()
        model_instance = DIDXResponse.deserialize(data)
        assert isinstance(model_instance, DIDXResponse)
