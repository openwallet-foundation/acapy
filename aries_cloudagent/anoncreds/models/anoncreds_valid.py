from base58 import alphabet
from marshmallow.validate import OneOf, Range, Regexp, Validator

B58 = alphabet if isinstance(alphabet, str) else alphabet.decode("ascii")


class AnonCredsSchemaId(Regexp):
    """Validate value against indy schema identifier specification."""

    EXAMPLE = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"
    PATTERN = rf"^[{B58}]{{21,22}}:2:.+:[0-9.]+$"

    def __init__(self):
        """Initializer."""

        super().__init__(
            AnonCredsSchemaId.PATTERN,
            error="Value {input} is not an indy schema identifier",
        )


class AnonCredsVersion(Regexp):
    """Validate value against indy version specification."""

    EXAMPLE = "1.0"
    PATTERN = r"^[0-9.]+$"

    def __init__(self):
        """Initializer."""

        super().__init__(
            AnonCredsVersion.PATTERN,
            error="Value {input} is not an indy version (use only digits and '.')",
        )


ANONCREDS_SCHEMA_ID = {
    "validate": AnonCredsSchemaId(),
    "example": AnonCredsSchemaId.EXAMPLE,
}
ANONCREDS_VERSION = {
    "validate": AnonCredsVersion(),
    "example": AnonCredsVersion.EXAMPLE,
}
