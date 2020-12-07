from unittest import mock, TestCase

from .. import __main__ as test_module


class TestMain(TestCase):
    def test_main(self):
        with mock.patch("aries_cloudagent.commands.run_command") as mock_run:
            args = ["aca-py", "--version"]
            test_module.main(args)

            mock_run.assert_called_once_with(None, args[1:])

    def test_ptvsd(self):
        with mock.patch("ptvsd.enable_attach") as mock_enable, mock.patch(
            "ptvsd.wait_for_attach"
        ) as mock_wait:
            test_module.init_debug(["aca-py", "--debug"])

            mock_enable.assert_called_once()
            mock_wait.assert_called_once()

    def test_pycharm(self):
        with mock.patch("pydevd_pycharm.settrace") as mock_trace:
            test_module.init_debug(["aca-py", "--debug-pycharm"])

            mock_trace.assert_called_once()
