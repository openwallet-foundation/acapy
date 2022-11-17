from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import TRANSACTION_REQUEST

from ..transaction_request import TransactionRequest


class TestConfig:
    test_transaction_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    test_signature_request = {
        "author_goal_code": "transaction.ledger.write",
        "context": "did:sov",
        "method": "add-signature",
        "signature_type": "<requested signature type>",
        "signer_goal_code": "transaction.endorse",
    }
    test_timing = {"expires_time": "1597708800"}
    test_transaction_type = "http://didcomm.org/sign-attachment/%VER/signature-request"
    test_messages_attach = {
        "@id": "143c458d-1b1c-40c7-ab85-4d16808ddf0a",
        "mime-type": "application/json",
        "data": {
            "json": {
                "endorser": "V4SGRU86Z58d6TV7PBUe6f",
                "identifier": "LjgpST2rjsoxYegQDRm7EL",
                "operation": {
                    "data": {
                        "attr_names": ["first_name", "last_name"],
                        "name": "test_schema",
                        "version": "2.1",
                    },
                    "type": "101",
                },
                "protocolVersion": 2,
                "reqId": 1597766666168851000,
                "signatures": {
                    "LjgpST2rjsox": "4uq1mUATKMn6Y9sTaGWyuPgjUEw5UBysWNbfSqCfnbm1Vnfw"
                },
                "taaAcceptance": {
                    "mechanism": "manual",
                    "taaDigest": "f50feca75664270842bd4202c2d6f23e4c6a7e0fc2feb9f62",
                    "time": 1597708800,
                },
            }
        },
    }


class TestTransactionRequest(TestCase, TestConfig):
    def setUp(self):
        self.transaction_request = TransactionRequest(
            transaction_id=self.test_transaction_id,
            signature_request=self.test_signature_request,
            timing=self.test_timing,
            transaction_type=self.test_transaction_type,
            messages_attach=self.test_messages_attach,
        )

    def test_init(self):
        """Test initialization."""
        assert self.transaction_request.transaction_id == self.test_transaction_id
        assert self.transaction_request.signature_request == self.test_signature_request
        assert self.transaction_request.timing == self.test_timing
        assert self.transaction_request.transaction_type == self.test_transaction_type
        assert self.transaction_request.messages_attach == self.test_messages_attach

    def test_type(self):
        """Test type."""
        assert self.transaction_request._type == DIDCommPrefix.qualify_current(
            TRANSACTION_REQUEST
        )

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "transaction_request.TransactionRequestSchema.load"
    )
    def test_deserialize(self, mock_transaction_request_schema_load):
        """
        Test deserialization.
        """
        obj = self.transaction_request

        transaction_request = TransactionRequest.deserialize(obj)
        mock_transaction_request_schema_load.assert_called_once_with(obj)

        assert transaction_request is mock_transaction_request_schema_load.return_value

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "transaction_request.TransactionRequestSchema.dump"
    )
    def test_serialize(self, mock_transaction_request_schema_dump):
        """
        Test serialization.
        """
        transaction_request_dict = self.transaction_request.serialize()
        mock_transaction_request_schema_dump.assert_called_once_with(
            self.transaction_request
        )

        assert (
            transaction_request_dict
            is mock_transaction_request_schema_dump.return_value
        )


class TestTransactionRequestSchema(AsyncTestCase, TestConfig):
    """Test transaction request schema."""

    async def test_make_model(self):
        transaction_request = TransactionRequest(
            transaction_id=self.test_transaction_id,
            signature_request=self.test_signature_request,
            timing=self.test_timing,
            transaction_type=self.test_transaction_type,
            messages_attach=self.test_messages_attach,
        )
        data = transaction_request.serialize()
        model_instance = TransactionRequest.deserialize(data)
        assert type(model_instance) is type(transaction_request)
