from ..message_factory import MessageFactory, MessageParseError
from ..message_types import MessageTypes

from ..connections.messages.connection_invitation import ConnectionInvitation
from ..connections.messages.connection_request import ConnectionRequest
from ..connections.messages.connection_response import ConnectionResponse

from ..credentials.messages.credential_offer import CredentialOffer
from ..credentials.messages.credential_request import CredentialRequest
from ..credentials.messages.credential import Credential

from ..proofs.messages.proof_request import ProofRequest
from ..proofs.messages.proof import Proof

from ..routing.messages.forward import Forward


from unittest import mock, TestCase


class TestMessageFactory(TestCase):

    no_type_message = {"a": "b"}
    unknown_type_message = {"@type": 1}

    def test_make_message_no_type(self):
        with self.assertRaises(MessageParseError) as context:
            MessageFactory.make_message(self.no_type_message)
        assert str(context.exception) == "Message does not contain '@type' parameter"

    def test_make_message_unknown_type(self):
        with self.assertRaises(MessageParseError) as context:
            MessageFactory.make_message(self.unknown_type_message)
        assert "Unrecognized message type" in str(context.exception)

    @mock.patch("indy_catalyst_agent.messaging.message_factory.ConnectionInvitation")
    @mock.patch("indy_catalyst_agent.messaging.message_factory.ConnectionRequest")
    @mock.patch("indy_catalyst_agent.messaging.message_factory.ConnectionResponse")
    @mock.patch("indy_catalyst_agent.messaging.message_factory.CredentialOffer")
    @mock.patch("indy_catalyst_agent.messaging.message_factory.CredentialRequest")
    @mock.patch("indy_catalyst_agent.messaging.message_factory.Credential")
    @mock.patch("indy_catalyst_agent.messaging.message_factory.ProofRequest")
    @mock.patch("indy_catalyst_agent.messaging.message_factory.Proof")
    @mock.patch("indy_catalyst_agent.messaging.message_factory.Forward")
    def test_message_class_initialized(
        self,
        mock_forward,
        mock_proof,
        mock_proof_request,
        mock_credential,
        mock_credential_request,
        mock_credential_offer,
        mock_connection_response,
        mock_connection_request,
        mock_connection_invitation,
    ):
        for message_type in MessageTypes:

            if message_type.name == "CONNECTION_INVITATION":
                this_mock = mock_connection_invitation
                obj = {"@type": message_type.value}

            elif message_type.name == "CONNECTION_REQUEST":
                this_mock = mock_connection_request
                obj = {"@type": message_type.value}

            elif message_type.name == "CONNECTION_RESPONSE":
                this_mock = mock_connection_response
                obj = {"@type": message_type.value}

            elif message_type.name == "CREDENTIAL_OFFER":
                this_mock = mock_credential_offer
                obj = {"@type": message_type.value}

            elif message_type.name == "CREDENTIAL_REQUEST":
                this_mock = mock_credential_request
                obj = {"@type": message_type.value}

            elif message_type.name == "CREDENTIAL":
                this_mock = mock_credential
                obj = {"@type": message_type.value}

            elif message_type.name == "PROOF_REQUEST":
                this_mock = mock_proof_request
                obj = {"@type": message_type.value}

            elif message_type.name == "PROOF":
                this_mock = mock_proof
                obj = {"@type": message_type.value}

            elif message_type.name == "FORWARD":
                this_mock = mock_forward
                obj = {"@type": message_type.value}

            return_value = MessageFactory.make_message(obj)
            this_mock.deserialize.assert_called_once_with(obj)
            assert return_value is this_mock.deserialize.return_value

