from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import ATTACHED_MESSAGE

from ..messages_attach import MessagesAttach


class TestConfig:
    test_author_did = "LjgpST2rjsoxYegQDRm7EL"
    test_author_verkey = "4uq1mUATWKZArwyuPgjUEw5UBysWNbkf2SN6SqVwbfSqCfnbm1Vnfw"
    test_endorser_did = "V4SGRU86Z58d6TV7PBUe6f"
    test_transaction_message = {
        "attr_names": ["first_name", "last_name"],
        "name": "test_schema",
        "version": "2.1",
    }
    test_mechanism = "manual"
    test_taaDigest = "f50feca7bd4202c2ab977006761d36bd6f23e4c6a7e0fc2feb9f62"
    test_time = 1597708800


class TestMessagesAttach(TestCase, TestConfig):
    def setUp(self):
        self.messages_attach = MessagesAttach(
            author_did=self.test_author_did,
            author_verkey=self.test_author_verkey,
            endorser_did=self.test_endorser_did,
            transaction_message=self.test_transaction_message,
            mechanism=self.test_mechanism,
            taaDigest=self.test_taaDigest,
            time=self.test_time,
        )

    def test_init(self):
        """Test initialization."""
        assert self.messages_attach.data["json"]["identifier"] == self.test_author_did
        assert self.messages_attach.data["json"]["signatures"] == {
            self.test_author_did: self.test_author_verkey
        }
        assert self.messages_attach.data["json"]["endorser"] == self.test_endorser_did
        assert (
            self.messages_attach.data["json"]["operation"]["data"]
            == self.test_transaction_message
        )
        assert (
            self.messages_attach.data["json"]["taaAcceptance"]["mechanism"]
            == self.test_mechanism
        )
        assert (
            self.messages_attach.data["json"]["taaAcceptance"]["taaDigest"]
            == self.test_taaDigest
        )
        assert (
            self.messages_attach.data["json"]["taaAcceptance"]["time"] == self.test_time
        )

    def test_type(self):
        """Test type."""
        assert self.messages_attach._type == DIDCommPrefix.qualify_current(
            ATTACHED_MESSAGE
        )

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "messages_attach.MessagesAttachSchema.load"
    )
    def test_deserialize(self, mock_messages_attach_schema_load):
        """
        Test deserialization.
        """
        obj = self.messages_attach

        messages_attach = MessagesAttach.deserialize(obj)
        mock_messages_attach_schema_load.assert_called_once_with(obj)

        assert messages_attach is mock_messages_attach_schema_load.return_value

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "messages_attach.MessagesAttachSchema.dump"
    )
    def test_serialize(self, mock_messages_attach_schema_dump):
        """
        Test serialization.
        """
        messages_attach_dict = self.messages_attach.serialize()
        mock_messages_attach_schema_dump.assert_called_once_with(self.messages_attach)

        assert messages_attach_dict is mock_messages_attach_schema_dump.return_value
