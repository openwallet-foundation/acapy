from marshmallow import ValidationError
from unittest import TestCase

from ..valid import (
    INDY_CRED_DEF_ID,
    INDY_SCHEMA_ID,
    INDY_PREDICATE,
    INDY_ISO8601_DATETIME
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
