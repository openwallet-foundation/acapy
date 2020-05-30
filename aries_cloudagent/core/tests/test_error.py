import asyncio

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ..error import BaseError


class TestBaseError(AsyncTestCase):
    async def test_base_error(self):
        err = BaseError()
        assert err.error_code is None
        assert not err.message
        assert not err.roll_up

        MESSAGE = "Not enough space\nClear 10MB\n\n"
        CODE = "-1"
        err = BaseError(MESSAGE, error_code=CODE)
        assert err.error_code == CODE
        assert err.message == MESSAGE.strip()
        assert err.roll_up == "Not enough space. Clear 10MB"

        iox = IOError("hello")
        keyx = KeyError("world")
        osx = OSError("oh\nno")
        osx.__cause__ = keyx
        iox.__cause__ = osx
        err.__cause__ = iox

        assert err.roll_up == "Not enough space. Clear 10MB. hello. oh. no. world"
