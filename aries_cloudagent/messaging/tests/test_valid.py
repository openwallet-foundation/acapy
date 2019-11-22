from marshmallow import ValidationError
from unittest import TestCase

from ..valid import (
    BASE64,
    BASE64URL,
    INDY_CRED_DEF_ID,
    INDY_DID,
    INDY_ISO8601_DATETIME,
    INDY_PREDICATE,
    INDY_RAW_PUBLIC_KEY,
    INDY_REV_REG_ID,
    INDY_SCHEMA_ID,
    INDY_VERSION,
    INT_EPOCH,
    SHA256,
    UUID4
)


class TestValid(TestCase):

    def test_epoch(self):
        non_epochs = [
            -9223372036854775809,
            9223372036854775808
        ]
        for non_epoch in non_epochs:
            with self.assertRaises(ValidationError):
                INT_EPOCH["validate"](non_epoch)

        INT_EPOCH["validate"](0)
        INT_EPOCH["validate"](2147483647)
        INT_EPOCH["validate"](-9223372036854775808)
        INT_EPOCH["validate"](9223372036854775807)

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
                INDY_DID["validate"](non_indy_did)

        INDY_DID["validate"]("Q4zqM7aXqm7gDQkUVLng9h")  # TODO: accept non-indy dids
        INDY_DID["validate"]("did:sov:Q4zqM7aXqm7gDQkUVLng9h")

    def test_indy_raw_public_key(self):
        non_indy_raw_public_keys = [
           "Q4zqM7aXqm7gDQkUVLng9JQ4zqM7aXqm7gDQkUVLng9I",  # 'I' not a base58 char
           "Q4zqM7aXqm7gDQkUVLng",  # too short
           "Q4zqM7aXqm7gDQkUVLngZZZZZZZZZZZZZZZZZZZZZZZZZ",  # too long
        ]
        for non_indy_raw_public_key in non_indy_raw_public_keys:
            with self.assertRaises(ValidationError):
                INDY_RAW_PUBLIC_KEY["validate"](non_indy_raw_public_key)

        INDY_RAW_PUBLIC_KEY["validate"]("Q4zqM7aXqm7gDQkUVLng9hQ4zqM7aXqm7gDQkUVLng9h")

    def test_cred_def_id(self):
        non_cred_def_ids = [
           "Q4zqM7aXqm7gDQkUVLng9h:4:CL:18:0",
           "Q4zqM7aXqm7gDQkUVLng9h::CL:18:0",
           "Q4zqM7aXqm7gDQkUVLng9I:3:CL:18:tag",
           "Q4zqM7aXqm7gDQkUVLng9h:3::18:tag",
           "Q4zqM7aXqm7gDQkUVLng9h:3:18:tag"
                            
        ]
        for non_cred_def_id in non_cred_def_ids:
            with self.assertRaises(ValidationError):
                INDY_CRED_DEF_ID["validate"](non_cred_def_id)

        INDY_CRED_DEF_ID["validate"]("Q4zqM7aXqm7gDQkUVLng9h:3:CL:18:tag")  # short
        INDY_CRED_DEF_ID["validate"](
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
            )
        ]
        for non_rev_reg_id in non_rev_reg_ids:
            with self.assertRaises(ValidationError):
                INDY_REV_REG_ID["validate"](non_rev_reg_id)

        INDY_REV_REG_ID["validate"](
            "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0",
        )  # short
        INDY_REV_REG_ID["validate"](
            "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:"
            "Q4zqM7aXqm7gDQkUVLng9h:2:bc-reg:1.0:tag:CL_ACCUM:0"
        )  # long

    def test_version(self):
        non_versions = [
            "-1",
            "",
            "3_5",
            "3.5a"
        ]
        for non_version in non_versions:
            with self.assertRaises(ValidationError):
                INDY_VERSION["validate"](non_version)

        INDY_VERSION["validate"]("1.0")
        INDY_VERSION["validate"](".05")
        INDY_VERSION["validate"]("1.2.3")
        INDY_VERSION["validate"]("..")  # perverse but technically OK

    def test_schema_id(self):
        non_schema_ids = [
            "Q4zqM7aXqm7gDQkUVLng9h:3:bc-reg:1.0",
            "Q4zqM7aXqm7gDQkUVLng9h::bc-reg:1.0",
            "Q4zqM7aXqm7gDQkUVLng9h:bc-reg:1.0",
            "Q4zqM7aXqm7gDQkUVLng9h:2:1.0",
            "Q4zqM7aXqm7gDQkUVLng9h:2::1.0",
            "Q4zqM7aXqm7gDQkUVLng9h:2:bc-reg:",
            "Q4zqM7aXqm7gDQkUVLng9h:2:bc-reg:1.0a",
            "Q4zqM7aXqm7gDQkUVLng9I:2:bc-reg:1.0"  # I is not in base58
        ]
        for non_schema_id in non_schema_ids:
            with self.assertRaises(ValidationError):
                INDY_SCHEMA_ID["validate"](non_schema_id)

        INDY_SCHEMA_ID["validate"]("Q4zqM7aXqm7gDQkUVLng9h:2:bc-reg:1.0")

    def test_predicate(self):
        non_predicates = [
            ">>",
            "",
            " >= ",
            "<<<=",
            "==",
            "=",
            "!="
        ]
        for non_predicate in non_predicates:
            with self.assertRaises(ValidationError):
                INDY_PREDICATE["validate"](non_predicate)

        INDY_PREDICATE["validate"]("<")
        INDY_PREDICATE["validate"]("<=")
        INDY_PREDICATE["validate"](">=")
        INDY_PREDICATE["validate"](">")

    def test_indy_date(self):
        non_datetimes = [
            "nope",
            "2020-01-01",
            "2020-01-01:00:00:00Z",
            "2020.01.01 00:00:00Z",
            "2020-01-01T00:00.123456+00:00",
            "2020-01-01T00:00:00.123456+0:00"
        ]
        for non_datetime in non_datetimes:
            with self.assertRaises(ValidationError):
                INDY_ISO8601_DATETIME["validate"](non_datetime)

        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00:00Z")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01T00:00:00Z")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01T00:00:00")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00:00")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00:00+00:00")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00:00-00:00")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00-00:00")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00:00.1-00:00")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00:00.123456-00:00")

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
                BASE64["validate"](non_base64)
            with self.assertRaises(ValidationError):
                BASE64URL["validate"](non_base64)

        BASE64["validate"]("")
        BASE64["validate"]("abcd123")  # some specs like JWT insist on no padding
        BASE64["validate"]("abcde")
        BASE64["validate"]("UG90YX+v")
        BASE64["validate"]("UG90Y+/=")
        BASE64["validate"]("UG90YX==")
        with self.assertRaises(ValidationError):
            BASE64["validate"]("UG90YX-v")

        BASE64URL["validate"]("")
        BASE64URL["validate"]("abcd123")  # some specs like JWT insist on no padding
        BASE64URL["validate"]("abcde")
        BASE64URL["validate"]("UG90YX-v")
        BASE64URL["validate"]("UG90Y-_=")
        BASE64URL["validate"]("UG90YX==")
        with self.assertRaises(ValidationError):
            BASE64URL["validate"]("UG90YX+v")

    def test_sha256(self):
        non_sha256s = [
            "####",
            "abcd123",
            "________________________________________________________________",
            "gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg",
        ]
        for non_sha256 in non_sha256s:
            with self.assertRaises(ValidationError):
                SHA256["validate"](non_sha256)

        SHA256["validate"](
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        SHA256["validate"](
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )

    def test_uuid4(self):
        non_uuid4s = [
            "123",
            "",
            "----",
            "3fa85f6-5717-4562-b3fc-2c963f66afa6",  # short a hex digit
            "3fa85f645-5717-4562-b3fc-2c963f66afa6",  # extra hex digit
            "3fa85f64-5717-f562-b3fc-2c963f66afa6"  # 13th hex digit is not 4
        ]
        for non_uuid4 in non_uuid4s:
            with self.assertRaises(ValidationError):
                UUID4["validate"](non_uuid4)

        UUID4["validate"]("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        UUID4["validate"]("3FA85F64-5717-4562-B3FC-2C963F66AFA6")  # upper case OK
