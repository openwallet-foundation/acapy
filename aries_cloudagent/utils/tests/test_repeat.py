from asynctest import mock, TestCase

from .. import repeat as test_module


class TestRepeat(TestCase):
    async def test_iter(self):
        expect = [5, 7, 11, 17, 25]
        seq = test_module.RepeatSequence(5, interval=5.0, backoff=0.25)
        assert [round(attempt.next_interval) for attempt in seq] == expect

        seq = test_module.RepeatSequence(2, interval=5.0, backoff=0.25)
        attempt = seq.start()
        attempt = attempt.next()
        async with attempt.timeout(interval=0.01):
            with self.assertRaises(StopIteration):
                attempt.next()

    async def test_aiter(self):
        seq = test_module.RepeatSequence(5, interval=5.0, backoff=0.25)
        sleeps = [0]

        async def sleep(timeout):
            sleeps.append(timeout)

        with mock.patch.object(test_module.asyncio, "sleep", sleep):
            expect = [0, 5, 7, 11, 17]
            seen = 0
            async for attempt in seq:
                assert round(sleeps[attempt.index - 1]) == expect[attempt.index - 1]
                seen += 1
            assert seen == len(expect)

    def test_repr(self):
        assert repr(
            test_module.RepeatSequence(5, interval=5.0, backoff=0.25)
        ).startswith("<RepeatSequence")
        assert repr(test_module.RepeatAttempt(None)).startswith("<RepeatAttempt")
