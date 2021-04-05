from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import TRANSACTION_JOB_TO_SEND

from ..transaction_job_to_send import TransactionJobToSend


class TestConfig:
    test_job = "TRANSACTION_AUTHOR"


class TestTransactionJobToSend(TestCase, TestConfig):
    def setUp(self):
        self.transaction_job_to_send = TransactionJobToSend(job=self.test_job)

    def test_init(self):
        """Test initialization."""
        assert self.transaction_job_to_send.job == self.test_job

    def test_type(self):
        """Test type."""
        assert self.transaction_job_to_send._type == DIDCommPrefix.qualify_current(
            TRANSACTION_JOB_TO_SEND
        )

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "transaction_job_to_send.TransactionJobToSendSchema.load"
    )
    def test_deserialize(self, mock_transaction_job_to_send_schema_load):
        """
        Test deserialization.
        """
        obj = self.transaction_job_to_send

        transaction_job_to_send = TransactionJobToSend.deserialize(obj)
        mock_transaction_job_to_send_schema_load.assert_called_once_with(obj)

        assert (
            transaction_job_to_send
            is mock_transaction_job_to_send_schema_load.return_value
        )

    @mock.patch(
        "aries_cloudagent.protocols.endorse_transaction.v1_0.messages."
        "transaction_job_to_send.TransactionJobToSendSchema.dump"
    )
    def test_serialize(self, mock_transaction_job_to_send_schema_dump):
        """
        Test serialization.
        """
        transaction_job_to_send_dict = self.transaction_job_to_send.serialize()
        mock_transaction_job_to_send_schema_dump.assert_called_once_with(
            self.transaction_job_to_send
        )

        assert (
            transaction_job_to_send_dict
            is mock_transaction_job_to_send_schema_dump.return_value
        )


class TestTransactionJobToSendSchema(AsyncTestCase, TestConfig):
    """Test transaction job to send schema."""

    async def test_make_model(self):
        transaction_job_to_send = TransactionJobToSend(job=self.test_job)
        data = transaction_job_to_send.serialize()
        model_instance = TransactionJobToSend.deserialize(data)
        assert type(model_instance) is type(transaction_job_to_send)
