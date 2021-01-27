from asynctest import mock as async_mock, TestCase as AsyncTestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CRED_20_ACK, PROTOCOL_PACKAGE

from .. import cred_ack as test_module
from ..cred_ack import V20CredAck


class TestV20CredAck(AsyncTestCase):
    """Credential ack tests."""

    async def test_init_type(self):
        """Test initializer and type."""
        cred_ack = V20CredAck()

        assert cred_ack._type == DIDCommPrefix.qualify_current(CRED_20_ACK)

    async def test_deserialize(self):
        """Test deserialization."""
        obj = V20CredAck()

        with async_mock.patch.object(
            test_module.V20CredAckSchema, "load", async_mock.MagicMock()
        ) as mock_load:
            cred_ack = V20CredAck.deserialize(obj)
            mock_load.assert_called_once_with(obj)

            assert cred_ack is mock_load.return_value

    async def test_serialize(self):
        """Test serialization."""
        obj = V20CredAck()

        with async_mock.patch.object(
            test_module.V20CredAckSchema, "dump", async_mock.MagicMock()
        ) as mock_dump:
            cred_ack_dict = obj.serialize()
            mock_dump.assert_called_once_with(obj)

            assert cred_ack_dict is mock_dump.return_value


class TestCredentialAckSchema(AsyncTestCase):
    """Test credential ack schema."""

    async def test_make_model(self):
        """Test making model."""
        cred_ack = V20CredAck()
        data = cred_ack.serialize()
        model_instance = V20CredAck.deserialize(data)
        assert isinstance(model_instance, V20CredAck)
