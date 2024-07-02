from unittest import TestCase

from ..non_rev_interval import IndyNonRevocationInterval

FROM = 1000000000
TO = 1234567890

INTERVAL_FROM = IndyNonRevocationInterval(timestamp_from=FROM)
INTERVAL_TO = IndyNonRevocationInterval(timestamp_to=TO)
INTERVAL = IndyNonRevocationInterval(timestamp_from=FROM, timestamp_to=TO)


class TestInterval(TestCase):
    """Non-revocation interval tests"""

    def test_serde(self):
        """Test serialization and deserialization."""
        for interval in (INTERVAL_FROM, INTERVAL_TO, INTERVAL):
            non_revo_dict = interval.serialize()
            assert non_revo_dict.get("from") == interval.timestamp_from
            assert non_revo_dict.get("to") == interval.timestamp_to

            model = IndyNonRevocationInterval.deserialize(non_revo_dict)
            assert (
                model.timestamp_from == interval.timestamp_from
                and model.timestamp_to == interval.timestamp_to
            )
            assert model.timestamp()

    def test_covers(self):
        """Test spanning check."""
        assert INTERVAL_FROM.covers(FROM)
        assert INTERVAL_FROM.covers(TO)
        assert INTERVAL_FROM.covers()

        assert INTERVAL_TO.covers(FROM)
        assert INTERVAL_TO.covers(TO)
        assert not INTERVAL_TO.covers()

        assert INTERVAL.covers(FROM)
        assert INTERVAL.covers(TO)
        assert not INTERVAL.covers()
