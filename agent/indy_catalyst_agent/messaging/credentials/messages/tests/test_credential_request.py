from ..credential_request import CredentialRequest, CredentialRequestSchema
from ....message_types import MessageTypes

from unittest import mock, TestCase


class TestCredentialRequest(TestCase):
    offer_json = "offer_json"
    credential_request_json = "credential_request_json"
    credential_values_json = "credential_values_json"

    def test_init(self):
        credential_request = CredentialRequest(
            offer_json=self.offer_json,
            credential_request_json=self.credential_request_json,
            credential_values_json=self.credential_values_json,
        )
        assert credential_request.offer_json == self.offer_json
        assert (
            credential_request.credential_request_json == self.credential_request_json
        )
        assert credential_request.credential_values_json == self.credential_values_json

    def test_type(self):
        credential_request = CredentialRequest(
            offer_json=self.offer_json,
            credential_request_json=self.credential_request_json,
            credential_values_json=self.credential_values_json,
        )

        assert credential_request._type == MessageTypes.CREDENTIAL_REQUEST.value

    @mock.patch(
        "indy_catalyst_agent.messaging.credentials.messages.credential_request.CredentialRequestSchema.load"
    )
    def test_deserialize(self, mock_credential_request_schema_load):
        obj = {"obj": "obj"}

        credential_request = CredentialRequest.deserialize(obj)
        mock_credential_request_schema_load.assert_called_once_with(obj)

        assert credential_request is mock_credential_request_schema_load.return_value

    @mock.patch(
        "indy_catalyst_agent.messaging.credentials.messages.credential_request.CredentialRequestSchema.dump"
    )
    def test_serialize(self, mock_credential_request_schema_dump):
        credential_request = CredentialRequest(
            offer_json=self.offer_json,
            credential_request_json=self.credential_request_json,
            credential_values_json=self.credential_values_json,
        )

        credential_request_dict = credential_request.serialize()
        mock_credential_request_schema_dump.assert_called_once_with(credential_request)

        assert (
            credential_request_dict is mock_credential_request_schema_dump.return_value
        )


class TestCredentialRequestSchema(TestCase):
    credential_request = CredentialRequest(
        offer_json="offer_json",
        credential_request_json="credential_request_json",
        credential_values_json="credential_values_json",
    )

    def test_make_model(self):
        data = self.credential_request.serialize()
        model_instance = CredentialRequest.deserialize(data)
        assert type(model_instance) is type(self.credential_request)
