import contextlib
from io import StringIO
from asynctest import mock

from .. import logging as test_module


class TestLoggingConfigurator:
    agent_label_arg_value = "Aries Cloud Agent"
    transport_arg_value = "transport"
    host_arg_value = "host"
    port_arg_value = "port"

    @mock.patch.object(test_module, "load_resource", autospec=True)
    @mock.patch.object(test_module, "fileConfig", autospec=True)
    def test_configure_default(self, mock_file_config, mock_load_resource):
        test_module.LoggingConfigurator.configure()

        mock_load_resource.assert_called_once_with(
            test_module.DEFAULT_LOGGING_CONFIG_PATH, "utf-8"
        )
        mock_file_config.assert_called_once_with(
            mock_load_resource.return_value, disable_existing_loggers=False
        )

    @mock.patch.object(test_module, "load_resource", autospec=True)
    @mock.patch.object(test_module, "fileConfig", autospec=True)
    def test_configure_path(self, mock_file_config, mock_load_resource):
        path = "a path"
        test_module.LoggingConfigurator.configure(path)

        mock_load_resource.assert_called_once_with(path, "utf-8")
        mock_file_config.assert_called_once_with(
            mock_load_resource.return_value, disable_existing_loggers=False
        )

    def test_banner(self):
        stdout = StringIO()
        with contextlib.redirect_stdout(stdout):
            test_label = "Aries Cloud Agent"
            test_did = "55GkHamhTU1ZbTbV2ab9DE"
            test_module.LoggingConfigurator.print_banner(test_label, {}, {}, test_did)
        output = stdout.getvalue()
        assert test_did in output
