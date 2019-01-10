import indy_catalyst_agent

from unittest import mock


class TestMain:
    transport_arg_value = "transport"
    host_arg_value = "host"
    port_arg_value = "port"

    @mock.patch("indy_catalyst_agent.PARSER.parse_args", autospec=True)
    @mock.patch("indy_catalyst_agent.Conductor", autospec=True)
    def test_main(self, mock_conductor, mock_parse_args):
        type(mock_parse_args.return_value).transport = self.transport_arg_value
        type(mock_parse_args.return_value).host = self.host_arg_value
        type(mock_parse_args.return_value).port = self.port_arg_value

        # Call function
        indy_catalyst_agent.main()

        mock_parse_args.assert_called_once()
        mock_conductor.assert_called_once_with(
            self.transport_arg_value, self.host_arg_value, self.port_arg_value
        )

        mock_conductor.return_value.start.assert_called_once_with()
