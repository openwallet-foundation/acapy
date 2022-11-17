from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import TRANSACTION_RESEND

from ..transaction_resend import TransactionResend


class TestConfig:
    test_thread_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    test_state = "resend"


class TestCancelTransaction(TestCase, TestConfig):
    def setUp(self):
        self.transaction_resend = TransactionResend(
            thread_id=self.test_thread_id, state=self.test_state
        )

    def test_init(self):
        """Test initialization."""
        assert self.transaction_resend.thread_id == self.test_thread_id
        assert self.transaction_resend.state == self.test_state

    def test_type(self):
        """Test type."""
        assert self.transaction_resend._type == DIDCommPrefix.qualify_current(
            TRANSACTION_RESEND
        )

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "transaction_resend.TransactionResendSchema.load"
    )
    def test_deserialize(self, mock_transaction_resend_schema_load):
        """
        Test deserialization.
        """
        obj = self.transaction_resend

        transaction_resend = TransactionResend.deserialize(obj)
        mock_transaction_resend_schema_load.assert_called_once_with(obj)

        assert transaction_resend is mock_transaction_resend_schema_load.return_value

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "transaction_resend.TransactionResendSchema.dump"
    )
    def test_serialize(self, mock_transaction_resend_schema_dump):
        """
        Test serialization.
        """
        transaction_resend_dict = self.transaction_resend.serialize()
        mock_transaction_resend_schema_dump.assert_called_once_with(
            self.transaction_resend
        )

        assert (
            transaction_resend_dict is mock_transaction_resend_schema_dump.return_value
        )


class TestTransactionResendSchema(AsyncTestCase, TestConfig):
    """Test transaction resend schema."""

    async def test_make_model(self):
        transaction_resend = TransactionResend(
            thread_id=self.test_thread_id, state=self.test_state
        )
        data = transaction_resend.serialize()
        model_instance = TransactionResend.deserialize(data)
        assert type(model_instance) is type(transaction_resend)
