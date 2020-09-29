from datetime import datetime
from unittest import TestCase

from ...util import datetime_to_str
from ..timing_decorator import TimingDecorator, TimingDecoratorSchema


NOW = datetime.now()


class TestTimingDecorator(TestCase):
    def test_serialize_load(self):
        deco = TimingDecorator(
            in_time=NOW,
            out_time=NOW,
        )

        assert deco.in_time == datetime_to_str(NOW)
        assert deco.out_time == datetime_to_str(NOW)
        assert not deco.stale_time
        assert not deco.expires_time
        assert not deco.delay_milli
        assert not deco.wait_until_time

        dumped = deco.serialize()
        loaded = TimingDecorator.deserialize(dumped)
