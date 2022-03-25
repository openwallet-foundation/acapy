from asynctest import mock as async_mock

from ..cache import ProfileCache


def test_get_not_in_cache():
    cache = ProfileCache(1)

    assert cache.get("1") is None


def test_put_get_in_cache():
    cache = ProfileCache(1)

    profile = async_mock.MagicMock()
    cache.put("1", profile)

    assert cache.get("1") is profile


def test_remove():
    cache = ProfileCache(1)

    profile = async_mock.MagicMock()
    cache.put("1", profile)

    assert cache.get("1") is profile

    cache.remove("1")

    assert cache.get("1") is None


def test_has_true():
    cache = ProfileCache(1)

    profile = async_mock.MagicMock()

    assert cache.has("1") is False
    cache.put("1", profile)
    assert cache.has("1") is True


def test_cleanup():
    cache = ProfileCache(1)

    profile1 = async_mock.MagicMock()
    profile2 = async_mock.MagicMock()

    cache.put("1", profile1)

    assert len(cache.profiles) == 1

    cache.put("2", profile2)

    assert len(cache.profiles) == 1
    assert cache.get("1") == None


def test_cleanup_lru():
    cache = ProfileCache(3)

    profile1 = async_mock.MagicMock()
    profile2 = async_mock.MagicMock()
    profile3 = async_mock.MagicMock()
    profile4 = async_mock.MagicMock()

    cache.put("1", profile1)
    cache.put("2", profile2)
    cache.put("3", profile3)

    assert len(cache.profiles) == 3

    cache.get("1")

    cache.put("4", profile4)

    assert len(cache.profiles) == 3
    assert cache.get("1") == profile1
    assert cache.get("2") == None
    assert cache.get("3") == profile3
    assert cache.get("4") == profile4
