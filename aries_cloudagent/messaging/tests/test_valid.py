from marshmallow import ValidationError
from unittest import TestCase

from ..valid import (
    BASE64,
    INDY_CRED_DEF_ID,
    INDY_SCHEMA_ID,
    INDY_PREDICATE,
    INDY_ISO8601_DATETIME,
    SHA256
)


class TestValid(TestCase):

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

        INDY_CRED_DEF_ID["validate"]("Q4zqM7aXqm7gDQkUVLng9h:3:CL:18:tag")

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
            "2020-01-01T00:00:00",
            "2020-01-01T00:00.123456+00:00",
            "2020-01-01T00:00:00.123456+0:00"
        ]
        for non_datetime in non_datetimes:
            with self.assertRaises(ValidationError):
                INDY_ISO8601_DATETIME["validate"](non_datetime)

        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00:00Z")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01T00:00:00Z")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00:00+00:00")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00:00-00:00")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00-00:00")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00:00.1-00:00")
        INDY_ISO8601_DATETIME["validate"]("2020-01-01 00:00:00.123456-00:00")

    def test_base64(self):
        non_base64s = [
            "####",
            "abcd123",
            "abcde===",
            "abcd====",
            "=abcd123",
            "=abcd123=",
            None
        ]
        for non_base64 in non_base64s:
            with self.assertRaises(ValidationError):
                BASE64["validate"](non_base64)

        BASE64["validate"]("")
        BASE64["validate"]("UG90YXRv")
        BASE64["validate"]("UG90YXR=")
        BASE64["validate"]("UG90YX==")

    def test_base64(self):
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
