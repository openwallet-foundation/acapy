from datetime import datetime, timezone
from unittest import mock, TestCase

from ..util import (
    b64_to_bytes,
    b64_to_str,
    bytes_to_b64,
    str_to_b64,
    set_urlsafe_b64,
    b58_to_bytes,
    bytes_to_b58,
)


BYTES = b"\xe0\xa0\xbe"  # chr(2110).encode(), least with + in b64 encoding
STR = "Hello World"


class TestUtil(TestCase):

    def test_b64_urlsafe(self):
        for urlsafe in (False, True):
            CHAR62 = ['+', '-']
            b64 = bytes_to_b64(BYTES, urlsafe=urlsafe)
            assert CHAR62[urlsafe] in b64

            b64 = set_urlsafe_b64(b64, urlsafe=urlsafe)
            assert CHAR62[urlsafe] in b64
            assert CHAR62[not urlsafe] not in b64

            b64 = set_urlsafe_b64(b64, urlsafe=(not urlsafe))
            assert CHAR62[urlsafe] not in b64
            assert CHAR62[not urlsafe] in b64

    def test_b64_str(self):
        b64 = str_to_b64(STR)
        assert b64_to_str(b64) == STR

        b64 = str_to_b64(STR, urlsafe=True)
        assert b64_to_str(b64, urlsafe=True) == STR
        assert b64_to_str(b64, encoding="ascii") == STR

    def test_b58(self):
        b58 = bytes_to_b58(BYTES)
        assert b58_to_bytes(b58) == BYTES
