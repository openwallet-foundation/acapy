from datetime import datetime, timezone
from unittest import mock, TestCase

from ..util import (
    datetime_now,
    datetime_to_str,
    epoch_to_str,
    str_to_datetime,
    str_to_epoch,
    time_now
)


class TestUtil(TestCase):
    def test_parse(self):
        now = datetime_now()
        assert isinstance(now, datetime)
        tests = {
            "2019-05-17 20:51:19.519437Z": datetime(
                2019, 5, 17, 20, 51, 19, 519437, tzinfo=timezone.utc
            ),
            "2019-05-17 20:51:19Z": datetime(
                2019, 5, 17, 20, 51, 19, 0, tzinfo=timezone.utc
            ),
            "2019-05-17 20:51Z": datetime(
                2019, 5, 17, 20, 51, 0, 0, tzinfo=timezone.utc
            ),
            "2019-11-15T22:37:14": datetime(
                2019, 11, 15, 22, 37, 14, tzinfo=timezone.utc
            ),
            "2019-05-17 20:51:19.519437+01:00": datetime(
                2019, 5, 17, 19, 51, 19, 519437, tzinfo=timezone.utc
            ),
            "2019-05-17T20:51:19.519437+0000": datetime(
                2019, 5, 17, 20, 51, 19, 519437, tzinfo=timezone.utc
            ),
            now: now,
        }
        for date_str, expected in tests.items():
            assert str_to_datetime(date_str) == expected
        with self.assertRaises(ValueError):
            str_to_datetime("BAD_DATE")

    def test_format(self):
        now = time_now()
        assert isinstance(now, str)
        tests = {
            datetime(
                2019, 5, 17, 20, 51, 19, 519437, tzinfo=timezone.utc
            ): "2019-05-17 20:51:19.519437Z",
            now: now,
        }
        for datetime_val, expected in tests.items():
            assert datetime_to_str(datetime_val) == expected

    def test_epoch(self):
        dt_now = datetime_now()
        epoch_now = int(dt_now.timestamp())

        assert epoch_now == str_to_epoch(dt_now) and isinstance(epoch_now, int)
        assert epoch_to_str(epoch_now) == datetime_to_str(dt_now.replace(microsecond=0))
