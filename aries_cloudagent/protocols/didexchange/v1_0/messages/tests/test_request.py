from unittest import mock

from asynctest import TestCase as AsyncTestCase

from pydid import DIDDocumentBuilder, VerificationSuite
from ......core.in_memory import InMemoryProfile
from ......messaging.decorators.attach_decorator import AttachDecorator

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import DIDX_REQUEST

from ..request import DIDXRequest


class TestConfig:
    test_seed = "testseed000000000000000000000001"
    test_did = "did:sov:55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_label = "Label"
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
        with builder.services.defaults() as services:
            services.add_didcomm(endpoint=endpoint,
                                 type_="IndyAgent",
                                 recipient_keys=[vmethod],
                                 routing_keys=[])
        return builder.build()


class TestDIDXRequest(AsyncTestCase, TestConfig):
    async def setUp(self):
        self.wallet = InMemoryProfile.test_session().wallet
        self.did_info = await self.wallet.create_local_did()

        did_doc_attach = AttachDecorator.from_indy_dict(self.make_did_doc().serialize())
        await did_doc_attach.data.sign(self.did_info.verkey, self.wallet)

        self.request = DIDXRequest(
            label=TestConfig.test_label,
            did=TestConfig.test_did,
            did_doc_attach=did_doc_attach,
        )

    def test_init(self):
        """Test initialization."""
        assert self.request.label == TestConfig.test_label
        assert self.request.did == TestConfig.test_did

    def test_type(self):
        """Test type."""
        assert self.request._type == DIDCommPrefix.qualify_current(DIDX_REQUEST)

    @mock.patch(
        "aries_cloudagent.protocols.didexchange.v1_0.messages."
        "request.DIDXRequestSchema.load"
    )
    def test_deserialize(self, mock_request_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        request = DIDXRequest.deserialize(obj)
        mock_request_schema_load.assert_called_once_with(obj)

        assert request is mock_request_schema_load.return_value

    @mock.patch(
        "aries_cloudagent.protocols.didexchange.v1_0.messages."
        "request.DIDXRequestSchema.dump"
    )
    def test_serialize(self, mock_request_schema_dump):
        """
        Test serialization.
        """
        request_dict = self.request.serialize()
        mock_request_schema_dump.assert_called_once_with(self.request)

        assert request_dict is mock_request_schema_dump.return_value


class TestDIDXRequestSchema(AsyncTestCase, TestConfig):
    """Test request schema."""

    async def setUp(self):
        self.wallet = InMemoryProfile.test_session().wallet
        self.did_info = await self.wallet.create_local_did()

        did_doc_attach = AttachDecorator.from_indy_dict(self.make_did_doc().serialize())
        await did_doc_attach.data.sign(self.did_info.verkey, self.wallet)

        self.request = DIDXRequest(
            label=TestConfig.test_label,
            did=TestConfig.test_did,
            did_doc_attach=did_doc_attach,
        )

    async def test_make_model(self):
        data = self.request.serialize()
        model_instance = DIDXRequest.deserialize(data)
        assert isinstance(model_instance, DIDXRequest)
