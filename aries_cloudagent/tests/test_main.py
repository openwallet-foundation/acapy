from unittest import mock, TestCase

from .. import __main__ as test_module


class TestMain(TestCase):
    def test_main(self):
        with mock.patch.object(test_module, "__name__", "__main__"), mock.patch.object(
            test_module, "init_debug", mock.MagicMock()
        ) as mock_debug, mock.patch.object(
            test_module, "run", mock.MagicMock()
        ) as mock_run:
            args = ["aca-py"]
            test_module.main(args)
            mock_debug.assert_called_once_with(args)
            mock_run.assert_called_once_with(args)

    def test_run(self):
        with mock.patch("aries_cloudagent.commands.run_command") as mock_run_command:
            args = ["aca-py", "--version"]
            test_module.run(args)

            mock_run_command.assert_called_once_with(None, args[1:])

    def test_run_command(self):
        with mock.patch("aries_cloudagent.commands.run_command") as mock_run_command:
            args = ["aca-py", "dummy-command", "--dummy-arg"]
            test_module.run(args)

            mock_run_command.assert_called_once_with("dummy-command", args[2:])

    def test_ptvsd(self):
        with mock.patch("builtins.__import__") as mock_import:
            test_module.init_debug(["aca-py", "--debug"])

            mock_import.assert_called_once()
            self.assertEqual(mock_import.call_args[0][0], "ptvsd")
            mock_import.return_value.enable_attach.assert_called_once()
            mock_import.return_value.wait_for_attach.assert_called_once()

    def test_ptvsd_import_x(self):
        with mock.patch("builtins.__import__") as mock_import:
            mock_import.side_effect = ImportError("no such package")
            test_module.init_debug(["aca-py", "--debug"])

    def test_pycharm(self):
        with mock.patch("builtins.__import__") as mock_import:
            test_module.init_debug(["aca-py", "--debug-pycharm"])

            mock_import.assert_called_once()
            self.assertEqual(mock_import.call_args[0][0], "pydevd_pycharm")
            mock_import.return_value.settrace.assert_called_once()

    def test_pycharm_import_x(self):
        with mock.patch("builtins.__import__") as mock_import:
            mock_import.side_effect = ImportError("no such package")
            test_module.init_debug(["aca-py", "--debug-pycharm"])
