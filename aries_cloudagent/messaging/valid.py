"""Validators for schema fields."""

from base58 import alphabet
from datetime import datetime
from marshmallow.validate import OneOf, Regexp

from .util import epoch_to_str

B58 = alphabet if isinstance(alphabet, str) else alphabet.decode("ascii")


class IndyCredDefId(Regexp):
    """Validate value against indy credential definition identifier specification."""

    EXAMPLE = "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag"

    def __init__(self):
        """Initializer."""

        super().__init__(
            rf"^[{B58}]{{21,22}}:3:CL:[1-9][0-9]*:.+$",
            error="Value {input} is not an indy credential definition identifier."
        )


class IndySchemaId(Regexp):
    """Validate value against indy schema identifier specification."""

    EXAMPLE = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"

    def __init__(self):
        """Initializer."""

        super().__init__(
            rf"^[{B58}]{{21,22}}:2:.+:[0-9.]+$",
            error="Value {input} is not an indy schema identifier."
        )


class IndyPredicate(OneOf):
    """Validate value against indy predicate."""

    EXAMPLE = ">="

    def __init__(self):
        """Initializer."""

        super().__init__(
            choices=["<", "<=", ">=", ">"],
            error="Value {input} must be one of {choices}."
        )


class IndyISO8601DateTime(Regexp):
    """Validate value against ISO 8601 datetime format, indy profile."""

    EXAMPLE = epoch_to_str(int(datetime.now().timestamp()))

    def __init__(self):
        """Initializer."""

        super().__init__(
            r"^(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d)"
            r"(?:\:(\d\d(?:\.\d{1,6})?))?([+-]\d\d:?\d\d|Z)$",
            error="Value {input} is not a date in valid format."
        )


# Instances for marshmallow schema specification
INDY_CRED_DEF_ID = {
    "validate": IndyCredDefId(),
    "example": IndyCredDefId.EXAMPLE
}
INDY_SCHEMA_ID = {
    "validate": IndySchemaId(),
    "example": IndySchemaId.EXAMPLE
}
INDY_PREDICATE = {
    "validate": IndyPredicate(),
    "example": IndyPredicate.EXAMPLE
}
INDY_ISO8601_DATETIME = {
    "validate": IndyISO8601DateTime(),
    "example": IndyISO8601DateTime.EXAMPLE
}
