from unittest import mock, TestCase

from ...message_types import CREDENTIAL_STORED, PROTOCOL_PACKAGE

from ..credential_stored import CredentialStored


class TestCredentialStored(TestCase):
    """Credential stored tests"""

    def test_init(self):
        """Test initializer"""
        credential_stored = CredentialStored()

    def test_type(self):
        """Test type"""
        credential_stored = CredentialStored()

        assert credential_stored._type == CREDENTIAL_STORED

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.credential_stored.CredentialStoredSchema.load"
    )
    def test_deserialize(self, mock_credential_stored_schema_load):
        """
        Test deserialize
        """
        obj = CredentialStored()

        credential_stored = CredentialStored.deserialize(obj)
        mock_credential_stored_schema_load.assert_called_once_with(obj)

        assert credential_stored is mock_credential_stored_schema_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.credential_stored.CredentialStoredSchema.dump"
    )
    def test_serialize(self, mock_credential_stored_schema_dump):
        """
        Test serialization.
        """
        obj = CredentialStored()

        credential_stored_dict = obj.serialize()
        mock_credential_stored_schema_dump.assert_called_once_with(obj)

        assert credential_stored_dict is mock_credential_stored_schema_dump.return_value


class TestCredentialStoredSchema(TestCase):
    """Test credential cred stored schema"""

    credential_stored = CredentialStored()

    def test_make_model(self):
        """Test making model."""
        data = self.credential_stored.serialize()
        model_instance = CredentialStored.deserialize(data)
        assert isinstance(model_instance, CredentialStored)
