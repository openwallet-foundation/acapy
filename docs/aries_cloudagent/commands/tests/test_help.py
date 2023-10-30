from unittest import mock
from unittest import IsolatedAsyncioTestCase

from .. import help as command


class TestHelp(IsolatedAsyncioTestCase):
    def test_exec_help(self):
        with mock.patch.object(
            command.ArgumentParser, "print_help"
        ) as mock_print_help, mock.patch(
            "builtins.print", mock.MagicMock()
        ) as mock_print:
            command.execute([])
            mock_print_help.assert_called_once()

            command.execute(["-v"])
            mock_print.assert_called_once_with(command.__version__)

    def test_main(self):
        with mock.patch.object(
            command, "__name__", "__main__"
        ) as mock_name, mock.patch.object(
            command, "execute", mock.MagicMock()
        ) as mock_execute:
            command.main()
            mock_execute.assert_called_once
