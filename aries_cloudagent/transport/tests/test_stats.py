from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...config.injection_context import InjectionContext

from .. import stats as test_module


class TestStatsTracer(AsyncTestCase):
    def setUp(self):
        self.context = async_mock.MagicMock(
            socket_timer=async_mock.MagicMock(
                stop=async_mock.MagicMock(side_effect=AttributeError("wrong"))
            )
        )
        self.tracer = test_module.StatsTracer(test_module.Collector(), "test")

    async def test_queued_start_stop(self):
        await self.tracer.connection_queued_start(None, self.context, None)
        await self.tracer.connection_queued_end(None, self.context, None)

    async def test_connection_ready_error_pass(self):
        await self.tracer.connection_ready(None, self.context, None)
