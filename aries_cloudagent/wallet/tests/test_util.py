from unittest import TestCase

from ..util import (
    abbr_verkey,
    b58_to_bytes,
    b64_to_str,
    bytes_to_b58,
    bytes_to_b64,
    full_verkey,
    pad,
    str_to_b64,
    set_urlsafe_b64,
    unpad,
)


BYTES = b"\xe0\xa0\xbe"  # chr(2110).encode(), least with + in b64 encoding
STR = "Hello World"  # b64encodes to SGVsbG8gV29ybGQ=


class TestUtil(TestCase):
    def test_b64_urlsafe(self):
        for urlsafe in (False, True):
            CHAR62 = ["+", "-"]
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
        assert "=" in b64
        assert b64_to_str(b64) == STR

        b64 = str_to_b64(STR, pad=False)
        assert "=" not in b64
        assert b64_to_str(b64) == STR

        b64 = str_to_b64(STR, urlsafe=True)
        assert "=" in b64
        assert b64_to_str(b64, urlsafe=True) == STR
        assert b64_to_str(b64, urlsafe=True, encoding="ascii") == STR

        b64 = str_to_b64(STR, urlsafe=True, pad=False)
        assert "=" not in b64
        assert b64_to_str(b64, urlsafe=True) == STR
        assert b64_to_str(b64, urlsafe=True, encoding="ascii") == STR

    def test_pad(self):
        assert pad("SGVsbG8gV29ybGQ") == "SGVsbG8gV29ybGQ="
        assert unpad("SGVsbG8gV29ybGQ=") == "SGVsbG8gV29ybGQ"

        assert pad("SGVsbG8gV29ybGQx") == "SGVsbG8gV29ybGQx"
        assert unpad("SGVsbG8gV29ybGQx") == "SGVsbG8gV29ybGQx"

    def test_b58(self):
        b58 = bytes_to_b58(BYTES)
        assert b58_to_bytes(b58) == BYTES

    def test_full_abbr_verkey(self):
        did = "N76kAdywAdHCySjgymbZ9t"
        full_vk = "CWBBfFmEVUDbs7rSCeKaFKfaeYXS2dKynAk7e2sCv23b"
        abbr_vk = "~79woMYnyEk6XnQaBA39i57"

        full = full_verkey(did, abbr_vk)
        assert full == full_vk
        assert full == full_verkey(f"did:sov:{did}", abbr_vk)
        assert full_verkey(did, full_vk) == full_vk

        abbr = abbr_verkey(full_vk)
        abbr_did = abbr_verkey(full_vk, did)
        abbr_qdid = abbr_verkey(full_vk, f"did:sov:{did}")
        assert abbr_did == abbr_qdid == abbr == abbr_vk
