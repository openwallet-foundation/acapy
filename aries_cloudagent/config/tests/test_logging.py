from unittest import mock

from .. import logging as test_module


class TestLoggingConfigurator:
    transport_arg_value = "transport"
    host_arg_value = "host"
    port_arg_value = "port"

    @mock.patch.object(test_module.path, "join")
    @mock.patch.object(test_module, "fileConfig", autospec=True)
    def test_configure_default(self, mock_file_config, mock_os_path_join):
        test_module.LoggingConfigurator.configure()

        mock_file_config.assert_called_once_with(
            mock_os_path_join.return_value, disable_existing_loggers=False
        )

    @mock.patch.object(test_module.path, "join")
    @mock.patch.object(test_module, "fileConfig", autospec=True)
    def test_configure_path(self, mock_file_config, mock_os_path_join):
        path = "a path"
        test_module.LoggingConfigurator.configure(path)

        mock_file_config.assert_called_once_with(path, disable_existing_loggers=False)
