from ...core.profile import Profile

from ..cache import ProfileCache


class MockProfile(Profile):
    def session(self, context=None):
        ...

    def transaction(self, context=None):
        ...


def test_get_not_in_cache():
    cache = ProfileCache(1)

    assert cache.get("1") is None


def test_put_get_in_cache():
    cache = ProfileCache(1)

    profile = MockProfile()
    cache.put("1", profile)

    assert cache.get("1") is profile


def test_remove():
    cache = ProfileCache(1)

    profile = MockProfile()
    cache.put("1", profile)

    assert cache.get("1") is profile

    cache.remove("1")

    assert cache.get("1") is None


def test_has_true():
    cache = ProfileCache(1)

    profile = MockProfile()

    assert cache.has("1") is False
    cache.put("1", profile)
    assert cache.has("1") is True


def test_cleanup():
    cache = ProfileCache(1)

    cache.put("1", MockProfile())

    assert len(cache.profiles) == 1

    cache.put("2", MockProfile())

    assert len(cache.profiles) == 1
    assert cache.get("1") == None


def test_cleanup_lru():
    cache = ProfileCache(3)

    cache.put("1", MockProfile())
    cache.put("2", MockProfile())
    cache.put("3", MockProfile())

    assert len(cache.profiles) == 3

    cache.get("1")

    cache.put("4", MockProfile())

    assert len(cache._cache) == 3
    assert cache.get("1")
    assert cache.get("2") is None
    assert cache.get("3")
    assert cache.get("4")


def test_rescue_open_profile():
    cache = ProfileCache(3)

    cache.put("1", MockProfile())
    cache.put("2", MockProfile())
    cache.put("3", MockProfile())

    assert len(cache.profiles) == 3

    held = cache.profiles["1"]
    cache.put("4", MockProfile())

    assert len(cache.profiles) == 4
    assert len(cache._cache) == 3

    cache.get("1")

    assert len(cache.profiles) == 3
    assert len(cache._cache) == 3
    assert cache.get("1")
    assert cache.get("2") is None
    assert cache.get("3")
    assert cache.get("4")
