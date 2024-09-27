from unittest import TestCase, mock

from ......protocols.didcomm_prefix import DIDCommPrefix
from ...message_types import HANGUP, PROTOCOL_PACKAGE
from ...messages.hangup import Hangup


class TestHangup(TestCase):
    def test_init_type(self):
        """Test initializer."""

        obj = Hangup()
        assert obj._type == DIDCommPrefix.qualify_current(HANGUP)

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.hangup.HangupSchema.load")
    def test_deserialize(self, mock_hangup_schema_load):
        """Test deserialization."""

        obj = Hangup()
        hangup = Hangup.deserialize(obj)
        mock_hangup_schema_load.assert_called_once_with(obj)
        assert hangup is mock_hangup_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.hangup.HangupSchema.dump")
    def test_serialize(self, mock_hangup_schema_dump):
        """Test serialization."""

        obj = Hangup()
        hangup_dict = obj.serialize()
        mock_hangup_schema_dump.assert_called_once_with(obj)
        assert hangup_dict is mock_hangup_schema_dump.return_value

    def test_serde(self):
        """Test serialization and deserialization."""

        hangup = Hangup.deserialize({})
        assert hangup._type == DIDCommPrefix.qualify_current(HANGUP)

        hangup_dict = hangup.serialize()
        assert "@id" in hangup_dict
        assert "@type" in hangup_dict

    def test_make_model(self):
        """Test making model."""

        obj = Hangup()
        data = obj.serialize()
        model_instance = Hangup.deserialize(data)
        assert isinstance(model_instance, Hangup)
