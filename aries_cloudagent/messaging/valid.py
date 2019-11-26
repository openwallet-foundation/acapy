"""Validators for schema fields."""

from datetime import datetime

from base58 import alphabet
from marshmallow.validate import OneOf, Range, Regexp

from .util import epoch_to_str

B58 = alphabet if isinstance(alphabet, str) else alphabet.decode("ascii")


class IntEpoch(Range):
    """Validate value against (integer) epoch format."""

    EXAMPLE = int(datetime.now().timestamp())

    def __init__(self):
        """Initializer."""

        super().__init__(  # use 64-bit for Aries RFC compatibility
            min=-9223372036854775808,
            max=9223372036854775807,
            error="Value {input} is not a valid integer epoch time."
        )


class IndyDID(Regexp):
    """Validate value against indy DID."""

    EXAMPLE = "WgWxqztrNooG92RXvxSTWv"

    def __init__(self):
        """Initializer."""

        super().__init__(
            rf"^(did:sov:)?[{B58}]{{21,22}}$",
            error="Value {input} is not an indy decentralized identifier (DID)."
        )


class IndyRawPublicKey(Regexp):
    """Validate value against indy (Ed25519VerificationKey2018) raw public key."""

    EXAMPLE = "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"

    def __init__(self):
        """Initializer."""

        super().__init__(
            rf"^[{B58}]{{43,44}}$",
            error="Value {input} is not a raw Ed25519VerificationKey2018 key."
        )


class IndyCredDefId(Regexp):
    """Validate value against indy credential definition identifier specification."""

    EXAMPLE = "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag"

    def __init__(self):
        """Initializer."""

        super().__init__(
            (
                rf"([{B58}]{{21,22}})"  # issuer DID
                f":3"  # cred def id marker
                f":CL"  # sig alg
                rf":(([1-9][0-9]*)|([{B58}]{{21,22}}:2:.+:[0-9.]+))"  # schema txn / id
                f"(.+)?$"  # tag
            ),
            error="Value {input} is not an indy credential definition identifier."
        )


class IndyVersion(Regexp):
    """Validate value against indy version specification."""

    EXAMPLE = "1.0"

    def __init__(self):
        """Initializer."""

        super().__init__(
            rf"^[0-9.]+$",
            error="Value {input} is not an indy version (use only digits and '.')."
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


class IndyRevRegId(Regexp):
    """Validate value against indy revocation registry identifier specification."""

    EXAMPLE = f"WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0"

    def __init__(self):
        """Initializer."""

        super().__init__(
            (
                rf"^([{B58}]{{21,22}}):4:"
                rf"([{B58}]{{21,22}}):3:"
                rf"CL:(([1-9][0-9]*)|([{B58}]{{21,22}}:2:.+:[0-9.]+))(:.+)?:"
                rf"CL_ACCUM:.+$"
            ),
            error="Value {input} is not an indy revocation registry identifier."
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
            r"^\d{4}-\d\d-\d\d[T ]\d\d:\d\d"
            r"(?:\:(?:\d\d(?:\.\d{1,6})?))?(?:[+-]\d\d:?\d\d|Z|)$",
            error="Value {input} is not a date in valid format."
        )


class Base64(Regexp):
    """Validate base64 value."""

    EXAMPLE = "ey4uLn0="

    def __init__(self):
        """Initializer."""

        super().__init__(
            r"^[a-zA-Z0-9+/]*={0,2}$",
            error="Value {input} is not a valid base64 encoding"
        )


class Base64URL(Regexp):
    """Validate base64 value."""

    EXAMPLE = "ey4uLn0="

    def __init__(self):
        """Initializer."""

        super().__init__(
            r"^[-_a-zA-Z0-9]*={0,2}$",
            error="Value {input} is not a valid base64url encoding"
        )


class JSONWebToken(Regexp):
    """Validate JSON Web token."""

    EXAMPLE = (
        "eyJhbGciOiJFZERTQSJ9."
        "eyJhIjogIjAifQ."
        "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    )

    def __init__(self):
        """Initializer."""

        super().__init__(
            r"^[-_a-zA-Z0-9]*\.[-_a-zA-Z0-9]*\.[-_a-zA-Z0-9]*$",
            error="Value {input} is not a valid JSON Web token"
        )


class SHA256Hash(Regexp):
    """Validate (binhex-encoded) SHA256 value."""

    EXAMPLE = "617a48c7c8afe0521efdc03e5bb0ad9e655893e6b4b51f0e794d70fba132aacb"

    def __init__(self):
        """Initializer."""

        super().__init__(
            r"^[a-fA-F0-9+/]{64}$",
            error="Value {input} is not a valid (binhex-encoded) SHA-256 hash"
        )


class UUIDFour(Regexp):
    """Validate UUID4: 8-4-4-4-12 hex digits, the 13th of which being 4."""

    EXAMPLE = "3fa85f64-5717-4562-b3fc-2c963f66afa6"

    def __init__(self):
        """Initializer."""

        super().__init__(
            r"[a-fA-F0-9]{8}-"
            r"[a-fA-F0-9]{4}-"
            r"4[a-fA-F0-9]{3}-"
            r"[a-fA-F0-9]{4}-"
            r"[a-fA-F0-9]{12}",
            error="Value {input} is not a UUID4 (8-4-4-4-12 hex digits with digit#13=4)"
        )


# Instances for marshmallow schema specification
INT_EPOCH = {
    "validate": IntEpoch(),
    "example": IntEpoch.EXAMPLE
}
INDY_DID = {
    "validate": IndyDID(),
    "example": IndyDID.EXAMPLE
}
INDY_RAW_PUBLIC_KEY = {
    "validate": IndyRawPublicKey(),
    "example": IndyRawPublicKey.EXAMPLE
}
INDY_SCHEMA_ID = {
    "validate": IndySchemaId(),
    "example": IndySchemaId.EXAMPLE
}
INDY_CRED_DEF_ID = {
    "validate": IndyCredDefId(),
    "example": IndyCredDefId.EXAMPLE
}
INDY_REV_REG_ID = {
    "validate": IndyRevRegId(),
    "example": IndyRevRegId.EXAMPLE
}
INDY_VERSION = {
    "validate": IndyVersion(),
    "example": IndyVersion.EXAMPLE
}
INDY_PREDICATE = {
    "validate": IndyPredicate(),
    "example": IndyPredicate.EXAMPLE
}
INDY_ISO8601_DATETIME = {
    "validate": IndyISO8601DateTime(),
    "example": IndyISO8601DateTime.EXAMPLE
}
BASE64 = {
    "validate": Base64(),
    "example": Base64.EXAMPLE
}
BASE64URL = {
    "validate": Base64URL(),
    "example": Base64.EXAMPLE
}
SHA256 = {
    "validate": SHA256Hash(),
    "example": SHA256Hash.EXAMPLE
}
UUID4 = {
    "validate": UUIDFour(),
    "example": UUIDFour.EXAMPLE
}
