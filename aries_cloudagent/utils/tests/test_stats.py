from tempfile import NamedTemporaryFile

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ..stats import Collector


class TestStats(AsyncTestCase):
    async def test_fn_decorator(self):
        stats = Collector()

        @stats
        def test_fn():
            pass

        test_fn()
        assert set(stats.results["avg"]) == {
            "TestStats.test_fn_decorator.<locals>.test_fn"
        }

        with self.assertRaises(ValueError):
            stats(None)

    async def test_method_decorator(self):
        stats = Collector()

        class TestClass:
            @stats
            def test(self):
                pass

            @stats
            async def test_async(self):
                pass

            @stats.mark("marked", "marked2")
            def test_mark(self):
                pass

            def test_wrap(self):
                pass

            def test_wrap_again(self):
                pass

        instance = TestClass()

        stats.wrap(instance, ["test_wrap", "test_wrap_again"])
        instance.test()
        await instance.test_async()
        instance.test_mark()
        instance.test_wrap()

        assert set(stats.results["avg"]) == {
            "TestStats.test_method_decorator.<locals>.TestClass.test",
            "TestStats.test_method_decorator.<locals>.TestClass.test_async",
            "TestStats.test_method_decorator.<locals>.TestClass.test_mark",
            "marked",
            "marked2",
            "TestStats.test_method_decorator.<locals>.TestClass.test_wrap",
        }

        with self.assertRaises(AttributeError):
            stats.wrap(instance, "test_missing")

        with self.assertRaises(ValueError):
            stats.wrap(instance, "")

    async def test_disable(self):
        stats = Collector()
        assert stats.enabled
        stats.enabled = False

        stats.log("test", 1.0)
        assert not set(stats.results["avg"])

        stats.enabled = True
        stats.log("test", 1.0)
        assert stats.results["avg"] == {"test": 1.0}

    async def test_extract(self):
        tmp_file = NamedTemporaryFile()
        stats = Collector(log_path=tmp_file.name)

        stats.log("test", 1.0)
        stats.log("test", 2.0)

        results = stats.extract({"test", "a"})
        assert results["count"] == {"test": 2}
        assert results["total"] == {"test": 3.0}
        assert results["avg"] == {"test": 1.5}
        assert results["min"] == {"test": 1.0}
        assert results["max"] == {"test": 2.0}

        results = stats.extract([])
        assert not results["avg"]

        stats.reset()
        assert not stats.results["avg"]
