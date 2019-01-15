from .. import Conductor
from ..transport import InvalidTransportError

from unittest import mock, TestCase


class TestConductor(TestCase):

    good_args = ["http", "host", 80]
    invalid_host_args = ["invalid", "host", 80]

    @mock.patch("indy_catalyst_agent.conductor.HttpTransport", autospec=True)
    def test_http_start(self, mock_http_transport):
        conductor = Conductor(*self.good_args)
        conductor.start()

        mock_http_transport.assert_called_once_with(
            conductor.host, conductor.port, conductor.message_handler
        )

        mock_http_transport.return_value.setup.assert_called_once_with()

    def test_invalid_transport(self):
        conductor = Conductor(*self.invalid_host_args)
        with self.assertRaises(InvalidTransportError):
            conductor.start()

    @mock.patch(
        # Cannot use autospec due to bug:
        # https://bugs.python.org/issue23078
        "indy_catalyst_agent.conductor.MessageFactory.make_message"  # autospec=True
    )
    def test_message_handler(self, mock_make_message):
        conductor = Conductor(*self.good_args)
        _dict = {}
        conductor.message_handler(_dict)
        mock_make_message.ensure_called_once_with(_dict)

