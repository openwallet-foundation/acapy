from ..agent_message import AgentMessage

from unittest import mock, TestCase


class TestAgentMessage(TestCase):
    class BadImplementationClass(AgentMessage):
        pass

    def test_init(self):
        with self.assertRaises(TypeError) as context:
            self.BadImplementationClass()  # pylint: disable=E0110

        assert (
            str(context.exception)
            == "Can't instantiate abstract class BadImplementationClass with abstract methods _type"
        )

