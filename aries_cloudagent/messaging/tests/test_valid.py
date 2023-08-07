import json
from unittest import TestCase

from marshmallow import ValidationError

from ..valid import (
    BASE58_SHA256_HASH_VALIDATE,
    BASE64_VALIDATE,
    BASE64URL_NO_PAD_VALIDATE,
    BASE64URL_VALIDATE,
    CREDENTIAL_CONTEXT_VALIDATE,
    CREDENTIAL_TYPE_VALIDATE,
    DID_KEY_VALIDATE,
    DID_POSTURE_VALIDATE,
    ENDPOINT_TYPE_VALIDATE,
    ENDPOINT_VALIDATE,
    INDY_CRED_DEF_ID_VALIDATE,
    INDY_CRED_REV_ID_VALIDATE,
    INDY_DID_VALIDATE,
    INDY_EXTRA_WQL_VALIDATE,
    INDY_ISO8601_DATETIME_VALIDATE,
    INDY_PREDICATE_VALIDATE,
    INDY_RAW_PUBLIC_KEY_VALIDATE,
    INDY_REV_REG_ID_VALIDATE,
    INDY_REV_REG_SIZE_VALIDATE,
    INDY_SCHEMA_ID_VALIDATE,
    INDY_VERSION_VALIDATE,
    INDY_WQL_VALIDATE,
    INT_EPOCH_VALIDATE,
    JWS_HEADER_KID_VALIDATE,
    JWT_VALIDATE,
    NATURAL_NUM_VALIDATE,
    NUM_STR_NATURAL_VALIDATE,
    NUM_STR_WHOLE_VALIDATE,
    SHA256_VALIDATE,
    UUID4_VALIDATE,
    WHOLE_NUM_VALIDATE,
)


class TestValid(TestCase):
    def test_epoch(self):
        non_epochs = [-1, 18446744073709551616]
        for non_epoch in non_epochs:
            with self.assertRaises(ValidationError):
                INT_EPOCH_VALIDATE(non_epoch)

        INT_EPOCH_VALIDATE(0)
        INT_EPOCH_VALIDATE(2147483647)
        INT_EPOCH_VALIDATE(18446744073709551615)

    def test_whole(self):
        non_wholes = [-9223372036854775809, 2.3, "Hello", None]
        for non_whole in non_wholes:
            with self.assertRaises(ValidationError):
                WHOLE_NUM_VALIDATE(non_whole)

        WHOLE_NUM_VALIDATE(0)
        WHOLE_NUM_VALIDATE(1)
        WHOLE_NUM_VALIDATE(12345678901234567890)

    def test_natural(self):
        non_naturals = [-9223372036854775809, 2.3, "Hello", None]
        for non_naturals in non_naturals:
            with self.assertRaises(ValidationError):
                NATURAL_NUM_VALIDATE(non_naturals)

        NATURAL_NUM_VALIDATE(1)
        NATURAL_NUM_VALIDATE(12345678901234567890)

    def test_str_whole(self):
        non_str_wholes = ["-9223372036854775809", "Hello", "5.5", "4+3"]
        for non_str_whole in non_str_wholes:
            with self.assertRaises(ValidationError):
                NUM_STR_WHOLE_VALIDATE(non_str_whole)

        NUM_STR_WHOLE_VALIDATE("0")
        NUM_STR_WHOLE_VALIDATE("1")
        NUM_STR_WHOLE_VALIDATE("12345678901234567890")

    def test_str_natural(self):
        non_str_naturals = ["-9223372036854775809", "Hello", "0", "5.5"]
        for non_str_natural in non_str_naturals:
            with self.assertRaises(ValidationError):
                NUM_STR_NATURAL_VALIDATE(non_str_natural)

        NUM_STR_NATURAL_VALIDATE("1")
        NUM_STR_NATURAL_VALIDATE("2")
        NUM_STR_NATURAL_VALIDATE("12345678901234567890")

    def test_indy_rev_reg_size(self):
        non_indy_rr_sizes = [-9223372036854775809, 2.3, "Hello", 0, 3, 32769, None]
        for non_indy_rr_size in non_indy_rr_sizes:
            with self.assertRaises(ValidationError):
                INDY_REV_REG_SIZE_VALIDATE(non_indy_rr_size)

        INDY_REV_REG_SIZE_VALIDATE(4)
        INDY_REV_REG_SIZE_VALIDATE(5)
        INDY_REV_REG_SIZE_VALIDATE(32767)
        INDY_REV_REG_SIZE_VALIDATE(32768)

    def test_indy_did(self):
        non_indy_dids = [
            "Q4zqM7aXqm7gDQkUVLng9I",  # 'I' not a base58 char
            "Q4zqM7aXqm7gDQkUVLng",  # too short
            "Q4zqM7aXqm7gDQkUVLngZZZ",  # too long
            "did:sov:Q4zqM7aXqm7gDQkUVLngZZZ",  # too long
            "did:other:Q4zqM7aXqm7gDQkUVLng9h",  # specifies non-indy DID
        ]
        for non_indy_did in non_indy_dids:
            with self.assertRaises(ValidationError):
                INDY_DID_VALIDATE(non_indy_did)

        INDY_DID_VALIDATE("Q4zqM7aXqm7gDQkUVLng9h")
        INDY_DID_VALIDATE("did:sov:Q4zqM7aXqm7gDQkUVLng9h")

    def test_indy_raw_public_key(self):
        non_indy_raw_public_keys = [
            "Q4zqM7aXqm7gDQkUVLng9JQ4zqM7aXqm7gDQkUVLng9I",  # 'I' not a base58 char
            "Q4zqM7aXqm7gDQkUVLng",  # too short
            "Q4zqM7aXqm7gDQkUVLngZZZZZZZZZZZZZZZZZZZZZZZZZ",  # too long
        ]
        for non_indy_raw_public_key in non_indy_raw_public_keys:
            with self.assertRaises(ValidationError):
                INDY_RAW_PUBLIC_KEY_VALIDATE(non_indy_raw_public_key)

        INDY_RAW_PUBLIC_KEY_VALIDATE("Q4zqM7aXqm7gDQkUVLng9hQ4zqM7aXqm7gDQkUVLng9h")

    def test_jws_header_kid(self):
        non_kids = [
            "http://not-this.one",
            "did:sov:i",  # too short
            "did:key:Q4zqM7aXqm7gDQkUVLng9h"  # missing leading z
            "did:key:zI4zqM7aXqm7gDQkUVLng9h",  # 'I' not a base58 char
        ]
        for non_kid in non_kids:
            with self.assertRaises(ValidationError):
                JWS_HEADER_KID_VALIDATE(non_kid)

        JWS_HEADER_KID_VALIDATE("did:key:zQ4zqM7aXqm7gDQkUVLng9h")
        JWS_HEADER_KID_VALIDATE("did:sov:Q4zqM7aXqm7gDQkUVLng9h#abc-123")
        JWS_HEADER_KID_VALIDATE(
            "did:sov:Q4zqM7aXqm7gDQkUVLng9h?version-time=1234567890#abc-123"
        )
        JWS_HEADER_KID_VALIDATE(
            "did:sov:Q4zqM7aXqm7gDQkUVLng9h?version-time=1234567890&a=b#abc-123"
        )
        JWS_HEADER_KID_VALIDATE(
            "did:sov:Q4zqM7aXqm7gDQkUVLng9h;foo:bar=low;a=b?version-id=1&a=b#abc-123"
        )

    def test_jwt(self):
        non_jwts = [
            "abcde",
            "abcde+.abcde/.abcdef",
            "abcdef==.abcdef==.abcdef",
            "abcdef==..",
        ]

        for non_jwt in non_jwts:
            with self.assertRaises(ValidationError):
                JWT_VALIDATE(non_jwt)

        JWT_VALIDATE("abcdef.abcdef.abcdef")
        JWT_VALIDATE("abcde-.abcde_.abcdef")
        JWT_VALIDATE("abcde-..abcdef")

    def test_did_key(self):
        non_did_keys = [
            "http://not-this.one",
            "did:sov:i",  # wrong preamble
            "did:key:Q4zqM7aXqm7gDQkUVLng9h"  # missing leading z
            "did:key:zI4zqM7aXqm7gDQkUVLng9h",  # 'I' not a base58 char
        ]
        for non_did_key in non_did_keys:
            with self.assertRaises(ValidationError):
                DID_KEY_VALIDATE(non_did_key)

        DID_KEY_VALIDATE("did:key:zQ4zqM7aXqm7gDQkUVLng9h")

    def test_did_posture(self):
        non_did_postures = [
            "not-me",
            None,
            "PUBLIC",
            "Posted",
            "wallet only",
        ]
        for non_did_posture in non_did_postures:
            with self.assertRaises(ValidationError):
                DID_POSTURE_VALIDATE(non_did_posture)

        DID_POSTURE_VALIDATE("public")
        DID_POSTURE_VALIDATE("posted")
        DID_POSTURE_VALIDATE("wallet_only")

    def test_indy_base58_sha256_hash(self):
        non_base58_sha256_hashes = [
            "Q4zqM7aXqm7gDQkUVLng9JQ4zqM7aXqm7gDQkUVLng9I",  # 'I' not a base58 char
            "Q4zqM7aXqm7gDQkUVLng",  # too short
            "Q4zqM7aXqm7gDQkUVLngZZZZZZZZZZZZZZZZZZZZZZZZZ",  # too long
        ]
        for non_base58_sha256_hash in non_base58_sha256_hashes:
            with self.assertRaises(ValidationError):
                BASE58_SHA256_HASH_VALIDATE(non_base58_sha256_hash)

        BASE58_SHA256_HASH_VALIDATE("Q4zqM7aXqm7gDQkUVLng9hQ4zqM7aXqm7gDQkUVLng9h")

    def test_cred_def_id(self):
        non_cred_def_ids = [
            "Q4zqM7aXqm7gDQkUVLng9h:4:CL:18:0",
            "Q4zqM7aXqm7gDQkUVLng9h::CL:18:0",
            "Q4zqM7aXqm7gDQkUVLng9I:3:CL:18:tag",
            "Q4zqM7aXqm7gDQkUVLng9h:3::18:tag",
            "Q4zqM7aXqm7gDQkUVLng9h:3:18:tag",
        ]
        for non_cred_def_id in non_cred_def_ids:
            with self.assertRaises(ValidationError):
                INDY_CRED_DEF_ID_VALIDATE(non_cred_def_id)

        INDY_CRED_DEF_ID_VALIDATE("Q4zqM7aXqm7gDQkUVLng9h:3:CL:18:tag")  # short
        INDY_CRED_DEF_ID_VALIDATE(
            "Q4zqM7aXqm7gDQkUVLng9h:3:CL:Q4zqM7aXqm7gDQkUVLng9h:2:bc-reg:1.0:tag"
        )  # long

    def test_rev_reg_id(self):
        non_rev_reg_ids = [
            "WgWxqztrNooG92RXvxSTWv:2:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0",
            "WgWxqztrNooG92RXvxSTWI:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0",
            "WgWxqztrN:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0",
            "WgWxqztrNooG92RXvxSTWvZ:4:WgWxqztrNooG92RXvxSTWvZ:3:CL:20:tag:CL_XXXXX:0",
            "WgWxqztrNooG92RXvxSTWv::WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0",
            (
                "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:"
                "Q4zqM7aXqm7gDQkUVLng9h:3:bc-reg:1.0:tag:CL_ACCUM:0"
            ),
            (
                "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:"
                "Q4zqM7aXqm7gDQkUVLng9I:2:bc-reg:1.0:tag:CL_ACCUM:0"
            ),
        ]
        for non_rev_reg_id in non_rev_reg_ids:
            with self.assertRaises(ValidationError):
                INDY_REV_REG_ID_VALIDATE(non_rev_reg_id)

        INDY_REV_REG_ID_VALIDATE(
            "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0",
        )  # short
        INDY_REV_REG_ID_VALIDATE(
            "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:"
            "Q4zqM7aXqm7gDQkUVLng9h:2:bc-reg:1.0:tag:CL_ACCUM:0"
        )  # long

    def test_cred_rev_id(self):
        non_cred_rev_ids = ["Wg", "0", "-5", "3.14"]
        for non_cred_rev_id in non_cred_rev_ids:
            with self.assertRaises(ValidationError):
                INDY_CRED_REV_ID_VALIDATE(non_cred_rev_id)

        INDY_CRED_REV_ID_VALIDATE("1")
        INDY_CRED_REV_ID_VALIDATE("99999999")

    def test_version(self):
        non_versions = ["-1", "", "3_5", "3.5a"]
        for non_version in non_versions:
            with self.assertRaises(ValidationError):
                INDY_VERSION_VALIDATE(non_version)

        INDY_VERSION_VALIDATE("1.0")
        INDY_VERSION_VALIDATE(".05")
        INDY_VERSION_VALIDATE("1.2.3")
        INDY_VERSION_VALIDATE("..")  # perverse but technically OK

    def test_schema_id(self):
        non_schema_ids = [
            "Q4zqM7aXqm7gDQkUVLng9h:3:bc-reg:1.0",
            "Q4zqM7aXqm7gDQkUVLng9h::bc-reg:1.0",
            "Q4zqM7aXqm7gDQkUVLng9h:bc-reg:1.0",
            "Q4zqM7aXqm7gDQkUVLng9h:2:1.0",
            "Q4zqM7aXqm7gDQkUVLng9h:2::1.0",
            "Q4zqM7aXqm7gDQkUVLng9h:2:bc-reg:",
            "Q4zqM7aXqm7gDQkUVLng9h:2:bc-reg:1.0a",
            "Q4zqM7aXqm7gDQkUVLng9I:2:bc-reg:1.0",  # I is not in base58
        ]
        for non_schema_id in non_schema_ids:
            with self.assertRaises(ValidationError):
                INDY_SCHEMA_ID_VALIDATE(non_schema_id)

        INDY_SCHEMA_ID_VALIDATE("Q4zqM7aXqm7gDQkUVLng9h:2:bc-reg:1.0")

    def test_predicate(self):
        non_predicates = [">>", "", " >= ", "<<<=", "==", "=", "!="]
        for non_predicate in non_predicates:
            with self.assertRaises(ValidationError):
                INDY_PREDICATE_VALIDATE(non_predicate)

        INDY_PREDICATE_VALIDATE("<")
        INDY_PREDICATE_VALIDATE("<=")
        INDY_PREDICATE_VALIDATE(">=")
        INDY_PREDICATE_VALIDATE(">")

    def test_indy_date(self):
        non_datetimes = [
            "nope",
            "2020-01-01",
            "2020-01-01:00:00:00Z",
            "2020.01.01 00:00:00Z",
            "2020-01-01T00:00.123456+00:00",
            "2020-01-01T00:00:00.123456+0:00",
        ]
        for non_datetime in non_datetimes:
            with self.assertRaises(ValidationError):
                INDY_ISO8601_DATETIME_VALIDATE(non_datetime)

        INDY_ISO8601_DATETIME_VALIDATE("2020-01-01 00:00:00Z")
        INDY_ISO8601_DATETIME_VALIDATE("2020-01-01T00:00:00Z")
        INDY_ISO8601_DATETIME_VALIDATE("2020-01-01T00:00:00")
        INDY_ISO8601_DATETIME_VALIDATE("2020-01-01 00:00:00")
        INDY_ISO8601_DATETIME_VALIDATE("2020-01-01 00:00:00+00:00")
        INDY_ISO8601_DATETIME_VALIDATE("2020-01-01 00:00:00-00:00")
        INDY_ISO8601_DATETIME_VALIDATE("2020-01-01 00:00-00:00")
        INDY_ISO8601_DATETIME_VALIDATE("2020-01-01 00:00:00.1-00:00")
        INDY_ISO8601_DATETIME_VALIDATE("2020-01-01 00:00:00.123456-00:00")

    def test_indy_wql(self):
        non_wqls = [
            "nope",
            "[a, b, c]",
            "{1, 2, 3}",
            set(),
            '"Hello World"',
            None,
            "null",
            "true",
            False,
        ]
        for non_wql in non_wqls:
            with self.assertRaises(ValidationError):
                INDY_WQL_VALIDATE(non_wql)

        INDY_WQL_VALIDATE(json.dumps({}))
        INDY_WQL_VALIDATE(json.dumps({"a": "1234"}))
        INDY_WQL_VALIDATE(json.dumps({"a": "1234", "b": {"$not": "0"}}))
        INDY_WQL_VALIDATE(json.dumps({"$or": {"a": "1234", "b": "0"}}))

    def test_indy_extra_wql(self):
        non_xwqls = [
            "nope",
            "[a, b, c]",
            "{1, 2, 3}",
            set(),
            '"Hello World"',
            None,
            "null",
            "true",
            False,
            "{}",
            '{"no": "referent"}',
            '{"no": "referent", "another": "non-referent"}',
            '{"uuid": {"too many: "braces"}}}',
        ]
        for non_xwql in non_xwqls:
            with self.assertRaises(ValidationError):
                INDY_EXTRA_WQL_VALIDATE(non_xwql)

        INDY_EXTRA_WQL_VALIDATE(json.dumps({"uuid0": {"name::ident::marker": "1"}}))
        INDY_EXTRA_WQL_VALIDATE(
            json.dumps(
                {
                    "uuid0": {"attr::ident::marker": "1"},
                    "uuid1": {"attr::member::value": "655321"},
                    "uuid2": {"attr::code::value": {"$in": ["abc", "def", "ghi"]}},
                    "uuid3": {"attr::score::value": {"$neq": "0"}},
                }
            )
        )

    def test_base64(self):
        non_base64s = [
            "####",
            "abcde===",
            "abcd====",
            "=abcd123",
            "=abcd123=",
        ]

        for non_base64 in non_base64s:
            with self.assertRaises(ValidationError):
                BASE64_VALIDATE(non_base64)
            with self.assertRaises(ValidationError):
                BASE64URL_VALIDATE(non_base64)

        BASE64_VALIDATE("")
        BASE64_VALIDATE("abcd123")  # some specs like JWT insist on no padding
        BASE64_VALIDATE("abcde")
        BASE64_VALIDATE("UG90YX+v")
        BASE64_VALIDATE("UG90Y+/=")
        BASE64_VALIDATE("UG90YX==")
        with self.assertRaises(ValidationError):
            BASE64_VALIDATE("UG90YX-v")

        BASE64URL_VALIDATE("")
        BASE64URL_VALIDATE("abcd123")  # some specs like JWT insist on no padding
        BASE64URL_VALIDATE("abcde")
        BASE64URL_VALIDATE("UG90YX-v")
        BASE64URL_VALIDATE("UG90Y-_=")
        BASE64URL_VALIDATE("UG90YX==")
        with self.assertRaises(ValidationError):
            BASE64URL_VALIDATE("UG90YX+v")  # '+' is not a base64url char

        non_base64_no_pads = ["####", "abcde=", "ab=cde"]
        for non_base64_no_pad in non_base64_no_pads:
            with self.assertRaises(ValidationError):
                BASE64URL_NO_PAD_VALIDATE(non_base64_no_pad)

        BASE64URL_NO_PAD_VALIDATE("")
        BASE64URL_NO_PAD_VALIDATE("abcd123")
        BASE64URL_NO_PAD_VALIDATE("abcde")
        BASE64URL_NO_PAD_VALIDATE("UG90YX-v")
        BASE64URL_NO_PAD_VALIDATE("UG90Y-_")
        BASE64URL_NO_PAD_VALIDATE("UG90YX")
        with self.assertRaises(ValidationError):
            BASE64URL_NO_PAD_VALIDATE("UG90YX+v")  # '+' is not a base64url char

    def test_sha256(self):
        non_sha256s = [
            "####",
            "abcd123",
            "________________________________________________________________",
            "gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg",
        ]
        for non_sha256 in non_sha256s:
            with self.assertRaises(ValidationError):
                SHA256_VALIDATE(non_sha256)

        SHA256_VALIDATE(
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        SHA256_VALIDATE(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )

    def test_uuid4(self):
        non_uuid4s = [
            "123",
            "",
            "----",
            "3fa85f6-5717-4562-b3fc-2c963f66afa6",  # short a hex digit
            "3fa85f645-5717-4562-b3fc-2c963f66afa6",  # extra hex digit
            "3fa85f64-5717-f562-b3fc-2c963f66afa6",  # 13th hex digit is not 4
        ]
        for non_uuid4 in non_uuid4s:
            with self.assertRaises(ValidationError):
                UUID4_VALIDATE(non_uuid4)

        UUID4_VALIDATE("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        UUID4_VALIDATE("3FA85F64-5717-4562-B3FC-2C963F66AFA6")  # upper case OK

    def test_endpoint(self):
        non_endpoints = [
            "123",
            "",
            "/path/only",
            "https://1.2.3.4?query=true&url=false",
            "no-proto:8080/my/path",
            "smtp:8080/my/path#fragment",
        ]

        for non_endpoint in non_endpoints:
            with self.assertRaises(ValidationError):
                ENDPOINT_VALIDATE(non_endpoint)

        ENDPOINT_VALIDATE("http://github.com")
        ENDPOINT_VALIDATE("https://localhost:8080")
        ENDPOINT_VALIDATE("newproto://myhost.ca:8080/path")
        ENDPOINT_VALIDATE("ftp://10.10.100.90:8021")
        ENDPOINT_VALIDATE("zzzp://someplace.ca:9999/path")

    def test_endpoint_type(self):
        non_endpoint_types = [
            "123",
            "endpoint",
            "end point",
            "end-point",
            "profile",
            "linked_domains",
            None,
        ]

        for non_endpoint_type in non_endpoint_types:
            with self.assertRaises(ValidationError):
                ENDPOINT_TYPE_VALIDATE(non_endpoint_type)

        ENDPOINT_TYPE_VALIDATE("Endpoint")
        ENDPOINT_TYPE_VALIDATE("Profile")
        ENDPOINT_TYPE_VALIDATE("LinkedDomains")

    def test_credential_type(self):
        with self.assertRaises(ValidationError):
            CREDENTIAL_TYPE_VALIDATE([])

        with self.assertRaises(ValidationError):
            CREDENTIAL_TYPE_VALIDATE(["WrongType", "AnotherWrongType"])

        with self.assertRaises(ValidationError):
            CREDENTIAL_TYPE_VALIDATE(["VerifiableCredential"])

        CREDENTIAL_TYPE_VALIDATE(["VerifiableCredential", "AnotherType"])
        CREDENTIAL_TYPE_VALIDATE(["SomeType", "AnotherType", "VerifiableCredential"])

    def test_credential_context(self):
        with self.assertRaises(ValidationError):
            CREDENTIAL_CONTEXT_VALIDATE([])

        with self.assertRaises(ValidationError):
            CREDENTIAL_CONTEXT_VALIDATE([{}, "https://www.w3.org/2018/credentials/v1"])

        CREDENTIAL_CONTEXT_VALIDATE(["https://www.w3.org/2018/credentials/v1"])
        CREDENTIAL_CONTEXT_VALIDATE(
            ["https://www.w3.org/2018/credentials/v1", "https://some-other-context.com"]
        )
