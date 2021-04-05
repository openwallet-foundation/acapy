from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import REFUSED_TRANSACTION_RESPONSE

from ..refused_transaction_response import RefusedTransactionResponse


class TestConfig:
    test_transaction_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    test_thread_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    test_signature_response = {
        "message_id": "143c458d-1b1c-40c7-ab85-4d16808ddf0a",
        "context": "did:sov",
        "method": "add-signature",
        "signer_goal_code": "transaction.refuse",
    }
    test_state = "refused"
    test_endorser_did = "V4SGRU86Z58d6TV7PBUe6f"


class TestRefusedTransactionResponse(TestCase, TestConfig):
    def setUp(self):
        self.refused_transaction_response = RefusedTransactionResponse(
            transaction_id=self.test_transaction_id,
            thread_id=self.test_thread_id,
            signature_response=self.test_signature_response,
            state=self.test_state,
            endorser_did=self.test_endorser_did,
        )

    def test_init(self):
        """Test initialization."""
        assert (
            self.refused_transaction_response.transaction_id == self.test_transaction_id
        )
        assert self.refused_transaction_response.thread_id == self.test_thread_id
        assert (
            self.refused_transaction_response.signature_response
            == self.test_signature_response
        )
        assert self.refused_transaction_response.state == self.test_state
        assert self.refused_transaction_response.endorser_did == self.test_endorser_did

    def test_type(self):
        """Test type."""
        assert self.refused_transaction_response._type == DIDCommPrefix.qualify_current(
            REFUSED_TRANSACTION_RESPONSE
        )

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "refused_transaction_response.RefusedTransactionResponseSchema.load"
    )
    def test_deserialize(self, mock_refused_transaction_response_schema_load):
        """
        Test deserialization.
        """
        obj = self.refused_transaction_response

        refused_transaction_response = RefusedTransactionResponse.deserialize(obj)
        mock_refused_transaction_response_schema_load.assert_called_once_with(obj)

        assert (
            refused_transaction_response
            is mock_refused_transaction_response_schema_load.return_value
        )

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "refused_transaction_response.RefusedTransactionResponseSchema.dump"
    )
    def test_serialize(self, mock_refused_transaction_response_schema_dump):
        """
        Test serialization.
        """
        refused_transaction_response_dict = (
            self.refused_transaction_response.serialize()
        )
        mock_refused_transaction_response_schema_dump.assert_called_once_with(
            self.refused_transaction_response
        )

        assert (
            refused_transaction_response_dict
            is mock_refused_transaction_response_schema_dump.return_value
        )


class TestRefusedTransactionResponseSchema(AsyncTestCase, TestConfig):
    """Test refused transaction response schema."""

    async def test_make_model(self):
        refused_transaction_response = RefusedTransactionResponse(
            transaction_id=self.test_transaction_id,
            thread_id=self.test_thread_id,
            signature_response=self.test_signature_response,
            state=self.test_state,
            endorser_did=self.test_endorser_did,
        )
        data = refused_transaction_response.serialize()
        model_instance = RefusedTransactionResponse.deserialize(data)
        assert type(model_instance) is type(refused_transaction_response)
