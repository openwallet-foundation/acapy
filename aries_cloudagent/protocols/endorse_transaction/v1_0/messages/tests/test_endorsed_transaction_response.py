from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import ENDORSED_TRANSACTION_RESPONSE

from ..endorsed_transaction_response import EndorsedTransactionResponse


class TestConfig:
    test_transaction_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    test_thread_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    test_signature_response = {
        "message_id": "95f890bf-329f-4450-9d9d-89082077acf9",
        "context": "did:sov",
        "method": "add-signature",
        "signer_goal_code": "transaction.endorse",
        "signature_type": "<requested signature type>",
        "signature": {
            "4Sr8NmbMuq6SHLrh7Bv5sN": "2svZP3omPic2Y9xQMh2AVhTd6Hhbrt6Yxc6d9cbwNGLu"
        },
    }
    test_state = "endorsed"
    test_endorser_did = "V4SGRU86Z58d6TV7PBUe6f"


class TestEndorsedTransactionResponse(TestCase, TestConfig):
    def setUp(self):
        self.endorsed_transaction_response = EndorsedTransactionResponse(
            transaction_id=self.test_transaction_id,
            thread_id=self.test_thread_id,
            signature_response=self.test_signature_response,
            state=self.test_state,
            endorser_did=self.test_endorser_did,
        )

    def test_init(self):
        """Test initialization."""
        assert (
            self.endorsed_transaction_response.transaction_id
            == self.test_transaction_id
        )
        assert self.endorsed_transaction_response.thread_id == self.test_thread_id
        assert (
            self.endorsed_transaction_response.signature_response
            == self.test_signature_response
        )
        assert self.endorsed_transaction_response.state == self.test_state
        assert self.endorsed_transaction_response.endorser_did == self.test_endorser_did

    def test_type(self):
        """Test type."""
        assert (
            self.endorsed_transaction_response._type
            == DIDCommPrefix.qualify_current(ENDORSED_TRANSACTION_RESPONSE)
        )

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "endorsed_transaction_response.EndorsedTransactionResponseSchema.load"
    )
    def test_deserialize(self, mock_endorsed_transaction_response_schema_load):
        """
        Test deserialization.
        """
        obj = self.endorsed_transaction_response

        endorsed_transaction_response = EndorsedTransactionResponse.deserialize(obj)
        mock_endorsed_transaction_response_schema_load.assert_called_once_with(obj)

        assert (
            endorsed_transaction_response
            is mock_endorsed_transaction_response_schema_load.return_value
        )

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "endorsed_transaction_response.EndorsedTransactionResponseSchema.dump"
    )
    def test_serialize(self, mock_endorsed_transaction_response_schema_dump):
        """
        Test serialization.
        """
        endorsed_transaction_response_dict = (
            self.endorsed_transaction_response.serialize()
        )
        mock_endorsed_transaction_response_schema_dump.assert_called_once_with(
            self.endorsed_transaction_response
        )

        assert (
            endorsed_transaction_response_dict
            is mock_endorsed_transaction_response_schema_dump.return_value
        )


class TestEndorsedTransactionResponseSchema(AsyncTestCase, TestConfig):
    """Test endorsed transaction response schema."""

    async def test_make_model(self):
        endorsed_transaction_response = EndorsedTransactionResponse(
            transaction_id=self.test_transaction_id,
            thread_id=self.test_thread_id,
            signature_response=self.test_signature_response,
            state=self.test_state,
            endorser_did=self.test_endorser_did,
        )
        data = endorsed_transaction_response.serialize()
        model_instance = EndorsedTransactionResponse.deserialize(data)
        assert type(model_instance) is type(endorsed_transaction_response)
