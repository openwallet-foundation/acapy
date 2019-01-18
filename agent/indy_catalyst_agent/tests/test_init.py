import indy_catalyst_agent

from unittest import mock
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock


class TestAsyncMain(AsyncTestCase):

    parsed_transports = [["a", "b", "c"]]
    transport_arg_value = "transport"
    host_arg_value = "host"
    port_arg_value = "port"

    @mock.patch("indy_catalyst_agent.asyncio", autospec=True)
    @mock.patch("indy_catalyst_agent.LoggingConfigurator", autospec=True)
    @mock.patch("indy_catalyst_agent.parser.parse_args", autospec=True)
    @async_mock.patch("indy_catalyst_agent.Conductor", autospec=True)
    def test_main_parse(
        self, mock_conductor, mock_parse_args, mock_logging_configurator, mock_asyncio
    ):
        type(mock_parse_args.return_value).transport = self.transport_arg_value
        type(mock_parse_args.return_value).host = self.host_arg_value
        type(mock_parse_args.return_value).port = self.port_arg_value

        indy_catalyst_agent.main()

        mock_parse_args.assert_called_once()

    @async_mock.patch("indy_catalyst_agent.Conductor", autospec=True)
    async def test_main(self, mock_conductor):
        await indy_catalyst_agent.start(self.parsed_transports)

        mock_conductor.assert_called_once_with(self.parsed_transports)
        mock_conductor.return_value.start.assert_called_once_with()

