from unittest import mock

from indy_catalyst_agent import LoggingConfigurator


class TestLoggingConfigurator:
    transport_arg_value = "transport"
    host_arg_value = "host"
    port_arg_value = "port"

    @mock.patch("indy_catalyst_agent.logging.path.join", autospec=True)
    @mock.patch("indy_catalyst_agent.logging.fileConfig", autospec=True)
    def test_configure_default(self, mock_file_config, mock_os_path_join):
        LoggingConfigurator.configure()

        mock_file_config.assert_called_once_with(
            mock_os_path_join.return_value, disable_existing_loggers=False
        )

    @mock.patch("indy_catalyst_agent.logging.path.join", autospec=True)
    @mock.patch("indy_catalyst_agent.logging.fileConfig", autospec=True)
    def test_configure_path(self, mock_file_config, mock_os_path_join):
        path = "a path"
        LoggingConfigurator.configure(path)

        mock_file_config.assert_called_once_with(path, disable_existing_loggers=False)
