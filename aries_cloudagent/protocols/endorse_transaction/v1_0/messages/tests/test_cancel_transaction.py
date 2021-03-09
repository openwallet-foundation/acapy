from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CANCEL_TRANSACTION

from ..cancel_transaction import CancelTransaction


class TestConfig:
    test_thread_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    test_state = "cancelled"


class TestCancelTransaction(TestCase, TestConfig):
    def setUp(self):
        self.cancel_transaction = CancelTransaction(
            thread_id=self.test_thread_id, state=self.test_state
        )

    def test_init(self):
        """Test initialization."""
        assert self.cancel_transaction.thread_id == self.test_thread_id
        assert self.cancel_transaction.state == self.test_state

    def test_type(self):
        """Test type."""
        assert self.cancel_transaction._type == DIDCommPrefix.qualify_current(
            CANCEL_TRANSACTION
        )

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "cancel_transaction.CancelTransactionSchema.load"
    )
    def test_deserialize(self, mock_cancel_transaction_schema_load):
        """
        Test deserialization.
        """
        obj = self.cancel_transaction

        cancel_transaction = CancelTransaction.deserialize(obj)
        mock_cancel_transaction_schema_load.assert_called_once_with(obj)

        assert cancel_transaction is mock_cancel_transaction_schema_load.return_value

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "cancel_transaction.CancelTransactionSchema.dump"
    )
    def test_serialize(self, mock_cancel_transaction_schema_dump):
        """
        Test serialization.
        """
        cancel_transaction_dict = self.cancel_transaction.serialize()
        mock_cancel_transaction_schema_dump.assert_called_once_with(
            self.cancel_transaction
        )

        assert (
            cancel_transaction_dict is mock_cancel_transaction_schema_dump.return_value
        )


class TestCancelTransactionSchema(AsyncTestCase, TestConfig):
    """Test cancel transaction schema."""

    async def test_make_model(self):
        cancel_transaction = CancelTransaction(
            thread_id=self.test_thread_id, state=self.test_state
        )
        data = cancel_transaction.serialize()
        model_instance = CancelTransaction.deserialize(data)
        assert type(model_instance) is type(cancel_transaction)
