# from ..credential import Credential
# from ....message_types import MessageTypes
#
# from unittest import mock, TestCase
#
#
# class TestCredential(TestCase):
#     credential_json = "credential_json"
#     revocation_registry_id = "revocation_registry_id"
#
#     def test_init(self):
#         credential = Credential(
#             credential_json=self.credential_json,
#             revocation_registry_id=self.revocation_registry_id,
#         )
#         assert credential.credential_json == self.credential_json
#         assert credential.revocation_registry_id == self.revocation_registry_id
#
#     def test_type(self):
#         credential = Credential(
#             credential_json=self.credential_json,
#             revocation_registry_id=self.revocation_registry_id,
#         )
#
#         assert credential._type == MessageTypes.CREDENTIAL.value
#
#     @mock.patch(
#         "aries_cloudagent.messaging.credentials.messages."
#         + "credential.CredentialSchema.load"
#     )
#     def test_deserialize(self, mock_credential_schema_load):
#         obj = {"obj": "obj"}
#
#         credential = Credential.deserialize(obj)
#         mock_credential_schema_load.assert_called_once_with(obj)
#
#         assert credential is mock_credential_schema_load.return_value
#
#     @mock.patch(
#         "aries_cloudagent.messaging.credentials.messages."
#         + "credential.CredentialSchema.dump"
#     )
#     def test_serialize(self, mock_credential_schema_dump):
#         credential = Credential(
#             credential_json=self.credential_json,
#             revocation_registry_id=self.revocation_registry_id,
#         )
#
#         credential_dict = credential.serialize()
#         mock_credential_schema_dump.assert_called_once_with(credential)
#
#         assert credential_dict is mock_credential_schema_dump.return_value
#
#
# class TestCredentialSchema(TestCase):
#     credential = Credential(
#         credential_json="credential_json",
#         revocation_registry_id="revocation_registry_id",
#     )
#
#     def test_make_model(self):
#         data = self.credential.serialize()
#         model_instance = Credential.deserialize(data)
#         assert isinstance(model_instance, Credential)
