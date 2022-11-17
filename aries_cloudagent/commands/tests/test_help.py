from asynctest import mock as async_mock, TestCase as AsyncTestCase

from .. import help as command


class TestHelp(AsyncTestCase):
    def test_exec_help(self):
        with async_mock.patch.object(
            command.ArgumentParser, "print_help"
        ) as mock_print_help, async_mock.patch(
            "builtins.print", async_mock.MagicMock()
        ) as mock_print:
            command.execute([])
            mock_print_help.assert_called_once()

            command.execute(["-v"])
            mock_print.assert_called_once_with(command.__version__)

    def test_main(self):
        with async_mock.patch.object(
            command, "__name__", "__main__"
        ) as mock_name, async_mock.patch.object(
            command, "execute", async_mock.MagicMock()
        ) as mock_execute:
            command.main()
            mock_execute.assert_called_once
