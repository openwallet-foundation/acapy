from unittest import mock
from unittest import IsolatedAsyncioTestCase


from .. import stats as test_module


class TestStatsTracer(IsolatedAsyncioTestCase):
    def setUp(self):
        self.context = mock.MagicMock(
            socket_timer=mock.MagicMock(
                stop=mock.MagicMock(side_effect=AttributeError("wrong"))
            )
        )
        self.tracer = test_module.StatsTracer(test_module.Collector(), "test")

    async def test_queued_start_stop(self):
        await self.tracer.connection_queued_start(None, self.context, None)
        await self.tracer.connection_queued_end(None, self.context, None)

    async def test_connection_ready_error_pass(self):
        await self.tracer.connection_ready(None, self.context, None)
