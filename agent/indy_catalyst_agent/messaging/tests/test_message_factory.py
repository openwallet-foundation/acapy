from unittest import mock, TestCase

from ..message_factory import MessageFactory, MessageParseError

# from ..presentations.messages.proof_request import ProofRequest


class TestMessageFactory(TestCase):
    no_type_message = {"a": "b"}
    unknown_type_message = {"@type": 1}
    test_message_type = "MESSAGE"

    def setUp(self):
        self.factory = MessageFactory()

    def test_make_message_no_type(self):
        with self.assertRaises(MessageParseError) as context:
            self.factory.make_message(self.no_type_message)
        assert str(context.exception) == "Message does not contain '@type' parameter"

    def test_make_message_unknown_type(self):
        with self.assertRaises(MessageParseError) as context:
            self.factory.make_message(self.unknown_type_message)
        assert "Unrecognized message type" in str(context.exception)

    # def test_message_class_registration(self):
    #     mock_message = mock.MagicMock()
    #     mock_message.deserialize.return_value = ProofRequest()

    #     self.factory.register_message_types({self.test_message_type: mock_message})

    #     obj = {"@type": self.test_message_type}
    #     return_value = self.factory.make_message(obj)

    #     mock_message.deserialize.assert_called_once_with(obj)
    #     assert return_value is mock_message.deserialize.return_value

    # @mock.patch(
    #     "indy_catalyst_agent.messaging.proofs.messages.proof_request.ProofRequest"
    # )
    # def test_message_class_name_registration(self, mock_proof_request):
    #     self.factory.register_message_types(
    #         {
    #             self.test_message_type: (
    #                 "indy_catalyst_agent.messaging.proofs.messages."
    #                 + "proof_request.ProofRequest"
    #             )
    #         }
    #     )

    #     obj = {"@type": self.test_message_type}
    #     return_value = self.factory.make_message(obj)

    #     mock_proof_request.deserialize.assert_called_once_with(obj)
    #     assert return_value is mock_proof_request.deserialize.return_value
