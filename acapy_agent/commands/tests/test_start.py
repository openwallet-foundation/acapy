import sys
from unittest import IsolatedAsyncioTestCase

from acapy_agent.tests import mock

from ...config.error import ArgsParseError
from .. import start as test_module


class TestStart(IsolatedAsyncioTestCase):
    def test_bad_args(self):
        with self.assertRaises(ArgsParseError):
            test_module.execute([])

        with self.assertRaises(SystemExit):
            test_module.execute(["bad"])

    async def test_start_shutdown_app(self):
        mock_conductor = mock.MagicMock(
            setup=mock.CoroutineMock(),
            start=mock.CoroutineMock(),
            stop=mock.CoroutineMock(),
        )
        await test_module.start_app(mock_conductor)
        await test_module.shutdown_app(mock_conductor)

        mock_conductor.setup.assert_awaited_once()
        mock_conductor.start.assert_awaited_once()
        mock_conductor.stop.assert_awaited_once()

    def test_execute_ok(self):
        """Test the execute() function with patched asyncio.run."""
        with mock.patch.object(
            test_module, "run_app", mock.AsyncMock()
        ), mock.patch.object(
            test_module.asyncio, "run"
        ) as mock_asyncio_run:
            test_module.execute(["--some", "args"])
            mock_asyncio_run.assert_called_once()

    def test_execute_keyboard_interrupt(self):
        """Test the execute() function with a KeyboardInterrupt."""
        with mock.patch.object(
            test_module.asyncio, "run", side_effect=KeyboardInterrupt
        ), mock.patch.object(test_module, "LOGGER") as mock_logger:
            test_module.execute()
            mock_logger.info.assert_called_with("Interrupted by user")

    def test_execute_other_exception(self):
        """Test the execute() function with generic Exception."""
        with (
            mock.patch.object(
                test_module.asyncio, "run", side_effect=RuntimeError("boom")
            ),
            mock.patch.object(test_module, "LOGGER") as mock_logger,
            mock.patch.object(sys, "exit") as mock_exit,
        ):
            test_module.execute()
            mock_logger.exception.assert_called_once()
            mock_exit.assert_called_once_with(1)

    def test_main_executes_when_main(self):
        """Ensure main() calls execute() when __name__ == '__main__'."""
        with mock.patch.object(
            test_module, "__name__", "__main__"
        ), mock.patch.object(test_module, "execute") as mock_execute:
            test_module.main()
            mock_execute.assert_called_once()
