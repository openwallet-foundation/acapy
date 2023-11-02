from unittest import mock
from unittest import IsolatedAsyncioTestCase

from ... import commands as test_module


class TestInit(IsolatedAsyncioTestCase):
    def test_available(self):
        avail = test_module.available_commands()
        assert len(avail) == 4

    def test_run(self):
        with mock.patch.object(
            test_module, "load_command", mock.MagicMock()
        ) as mock_load:
            mock_module = mock.MagicMock()
            mock_module.execute = mock.MagicMock()
            mock_load.return_value = mock_module

            test_module.run_command("hello", ["world"])
            mock_load.assert_called_once()
            mock_module.execute.assert_called_once()
