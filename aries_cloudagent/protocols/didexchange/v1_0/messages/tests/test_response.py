from unittest import mock

from asynctest import TestCase as AsyncTestCase

from ......connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from ......core.in_memory import InMemoryProfile
from ......messaging.decorators.attach_decorator import AttachDecorator
from ......wallet.did_method import SOV, DIDMethods
from ......wallet.key_type import ED25519
from .....didcomm_prefix import DIDCommPrefix
from ...message_types import DIDX_RESPONSE
from ..response import DIDXResponse


class TestConfig:
    test_seed = "testseed000000000000000000000001"
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"

    def make_did_doc(self):
        doc = DIDDoc(did=self.test_did)
        controller = self.test_did
        ident = "1"
        pk_value = self.test_verkey
        pk = PublicKey(
            self.test_did,
            ident,
            pk_value,
            PublicKeyType.ED25519_SIG_2018,
            controller,
            False,
        )
        doc.set(pk)
        recip_keys = [pk]
        routing_keys = []
        service = Service(
            self.test_did,
            "indy",
            "IndyAgent",
            recip_keys,
            routing_keys,
            self.test_endpoint,
        )
        doc.set(service)
        return doc


class TestDIDXResponse(AsyncTestCase, TestConfig):
    async def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.session.profile.context.injector.bind_instance(DIDMethods, DIDMethods())
        self.wallet = self.session.wallet

        self.did_info = await self.wallet.create_local_did(
            method=SOV,
            key_type=ED25519,
        )

        did_doc_attach = AttachDecorator.data_base64(self.make_did_doc().serialize())
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
        self.session = InMemoryProfile.test_session()
        self.session.profile.context.injector.bind_instance(DIDMethods, DIDMethods())
        self.wallet = self.session.wallet

        self.did_info = await self.wallet.create_local_did(
            method=SOV,
            key_type=ED25519,
        )

        did_doc_attach = AttachDecorator.data_base64(self.make_did_doc().serialize())
        await did_doc_attach.data.sign(self.did_info.verkey, self.wallet)

        self.response = DIDXResponse(
            did=TestConfig.test_did,
            did_doc_attach=did_doc_attach,
        )

    async def test_make_model(self):
        data = self.response.serialize()
        model_instance = DIDXResponse.deserialize(data)
        assert isinstance(model_instance, DIDXResponse)
