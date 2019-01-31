from ..agent_message import AgentMessage

from unittest import mock, TestCase


class TestAgentMessage(TestCase):
    class BadImplementationClass(AgentMessage):
        pass

    def test_init(self):
        with self.assertRaises(TypeError) as context:
            self.BadImplementationClass()  # pylint: disable=E0110

        assert "Can't instantiate abstract" in str(context.exception)

