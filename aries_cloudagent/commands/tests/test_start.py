from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .. import start as command


class TestStart(AsyncTestCase):
    def test_bad_args(self):
        with async_mock.patch.object(
            command.ArgumentParser, "print_usage"
        ) as print_usage:
            with self.assertRaises(SystemExit):
                command.execute([])
            print_usage.assert_called_once()

        with self.assertRaises(SystemExit):
            command.execute(["bad"])

    def test_exec_start(self):
        with async_mock.patch.object(
            command, "start_app", autospec=True
        ) as start_app, async_mock.patch.object(
            command, "run_loop"
        ) as run_loop, async_mock.patch.object(
            command, "shutdown_app", autospec=True
        ) as shutdown_app:
            command.execute(["-it", "http", "0.0.0.0", "80", "-ot", "http"])
            start_app.assert_called_once()
            assert isinstance(start_app.call_args[0][0], command.Conductor)
            shutdown_app.assert_called_once()
            assert isinstance(shutdown_app.call_args[0][0], command.Conductor)
            run_loop.assert_called_once()

    async def test_run_loop(self):
        startup = async_mock.CoroutineMock()
        startup_call = startup()
        shutdown = async_mock.CoroutineMock()
        shutdown_call = shutdown()
        with async_mock.patch.object(command, "asyncio", autospec=True) as mock_asyncio:
            command.run_loop(startup_call, shutdown_call)
            mock_asyncio.get_event_loop.return_value.add_signal_handler.assert_called_once()
            init_coro = mock_asyncio.ensure_future.call_args[0][0]
            mock_asyncio.get_event_loop.return_value.run_forever.assert_called_once()
            await init_coro
            startup.assert_awaited_once()

            done_calls = (
                mock_asyncio.get_event_loop.return_value.add_signal_handler.call_args
            )
            done_calls[0][1]()  # exec partial
            done_coro = mock_asyncio.ensure_future.call_args[0][0]
            task = async_mock.MagicMock()
            mock_asyncio.gather = async_mock.CoroutineMock()
            mock_asyncio.Task.all_tasks.return_value = [task]
            mock_asyncio.Task.current_task.return_value = task
            await done_coro
            shutdown.assert_awaited_once()
