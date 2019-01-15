from ..credential import Credential, CredentialSchema
from ...message_types import MessageTypes

from unittest import mock, TestCase


class TestCredential(TestCase):
    credential_json = "credential_json"
    revocation_registry_id = "revocation_registry_id"

    def test_init(self):
        credential = Credential(self.credential_json, self.revocation_registry_id)
        assert credential.credential_json == self.credential_json
        assert credential.revocation_registry_id == self.revocation_registry_id

    def test_type(self):
        credential = Credential(self.credential_json, self.revocation_registry_id)

        assert credential._type == MessageTypes.CREDENTIAL.value

    @mock.patch(
        "indy_catalyst_agent.messaging.credentials.credential.CredentialSchema.load"
    )
    def test_deserialize(self, mock_credential_schema_load):
        obj = {"obj": "obj"}

        credential = Credential.deserialize(obj)
        mock_credential_schema_load.assert_called_once_with(obj)

        assert credential is mock_credential_schema_load.return_value

    @mock.patch(
        "indy_catalyst_agent.messaging.credentials.credential.CredentialSchema.dump"
    )
    def test_serialize(self, mock_credential_schema_dump):
        credential = Credential(self.credential_json, self.revocation_registry_id)

        credential_dict = credential.serialize()
        mock_credential_schema_dump.assert_called_once_with(credential)

        assert credential_dict is mock_credential_schema_dump.return_value


class TestCredentialSchema(TestCase):
    credential = Credential("credential_json", "revocation_registry_id")

    def test_make_model(self):
        schema = CredentialSchema()

        data = self.credential.serialize()
        data["_type"] = data["@type"]
        del data["@type"]

        model_instance = schema.make_model(data)
        assert type(model_instance) is type(self.credential)

