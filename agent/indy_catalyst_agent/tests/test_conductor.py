from .. import Conductor
from ..transport import InvalidTransportError

from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock


class TestConductor(TestCase):

    good_args = [{"transport": "http", "host": "host", "port": 80}]
    invalid_host_args = [{"transport": "bad", "host": "host", "port": 80}]

    @mock.patch(
        # Cannot use autospec due to bug:
        # https://bugs.python.org/issue23078
        "indy_catalyst_agent.conductor.MessageFactory.make_message"  # autospec=True
    )
    def test_message_handler(self, mock_make_message):
        conductor = Conductor(self.good_args)
        conductor.dispatcher = mock.MagicMock()

        _dict = {}
        conductor.message_handler(_dict)
        mock_make_message.ensure_called_once_with(_dict)
        conductor.dispatcher.ensure_called_once_with(mock_make_message.return_value)


class TestAsyncConductor(AsyncTestCase):
    good_args = [{"transport": "http", "host": "host", "port": 80}]
    invalid_host_args = [{"transport": "bad", "host": "host", "port": 80}]

    @async_mock.patch("indy_catalyst_agent.conductor.HttpTransport", autospec=True)
    async def test_http_start(self, mock_http_transport):
        conductor = Conductor(self.good_args)
        await conductor.start()

        mock_http_transport.assert_called_once_with(
            self.good_args[0]["host"],
            self.good_args[0]["port"],
            conductor.message_handler,
        )
        mock_http_transport.return_value.start.assert_called_once_with()

    @async_mock.patch("indy_catalyst_agent.conductor.HttpTransport", autospec=True)
    async def test_invalid_transport(self, mock_http_transport):
        conductor = Conductor(self.invalid_host_args)
        with self.assertRaises(InvalidTransportError):
            await conductor.start()
