"""AnonCreds credential revocation models."""

from marshmallow import fields, validate, validates_schema
from marshmallow.exceptions import ValidationError

from .....messaging.models.openapi import OpenAPISchema
from .....messaging.valid import (
    ANONCREDS_REV_REG_ID_EXAMPLE,
    ANONCREDS_REV_REG_ID_VALIDATE,
    UUID4_EXAMPLE,
    UUID4_VALIDATE,
)
from ....models.issuer_cred_rev_record import (
    IssuerCredRevRecordSchemaAnonCreds,
)
from ...common.schemas import (
    CredRevRecordQueryStringMixin,
    EndorserOptionsSchema,
    RevocationIdsDictMixin,
)


class CredRevRecordQueryStringSchema(CredRevRecordQueryStringMixin):
    """Parameters and validators for credential revocation record request."""

    pass


class CredRevRecordResultSchemaAnonCreds(OpenAPISchema):
    """Result schema for credential revocation record request."""

    result = fields.Nested(IssuerCredRevRecordSchemaAnonCreds())


class PublishRevocationsOptions(EndorserOptionsSchema):
    """Options for publishing revocations to ledger."""

    pass


class PublishRevocationsSchemaAnonCreds(RevocationIdsDictMixin):
    """Request and result schema for revocation publication API call."""

    options = fields.Nested(PublishRevocationsOptions())


class PublishRevocationsResultSchemaAnonCreds(RevocationIdsDictMixin):
    """Result schema for credential definition send request."""

    pass


class RevokeRequestSchemaAnonCreds(CredRevRecordQueryStringSchema):
    """Parameters and validators for revocation request."""

    @validates_schema
    def validate_fields(self, data: dict, **kwargs) -> None:
        """Validate fields - connection_id and thread_id must be present if notify."""
        super().validate_fields(data, **kwargs)

        notify = data.get("notify")
        connection_id = data.get("connection_id")
        notify_version = data.get("notify_version", "v1_0")

        if notify and not connection_id:
            raise ValidationError("Request must specify connection_id if notify is true")
        if notify and not notify_version:
            raise ValidationError("Request must specify notify_version if notify is true")

    publish = fields.Boolean(
        required=False,
        metadata={
            "description": (
                "(True) publish revocation to ledger immediately, or (default, False)"
                " mark it pending"
            )
        },
    )
    notify = fields.Boolean(
        required=False,
        metadata={"description": "Send a notification to the credential recipient"},
    )
    notify_version = fields.String(
        validate=validate.OneOf(["v1_0", "v2_0"]),
        required=False,
        metadata={
            "description": (
                "Specify which version of the revocation notification should be sent"
            )
        },
    )
    connection_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": (
                "Connection ID to which the revocation notification will be sent;"
                " required if notify is true"
            ),
            "example": UUID4_EXAMPLE,
        },
    )
    thread_id = fields.Str(
        required=False,
        metadata={
            "description": (
                "Thread ID of the credential exchange message thread resulting in the"
                " credential now being revoked; required if notify is true"
            )
        },
    )
    comment = fields.Str(
        required=False,
        metadata={
            "description": "Optional comment to include in revocation notification"
        },
    )
    options = PublishRevocationsOptions()


class AnonCredsRevRegIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking rev reg id."""

    rev_reg_id = fields.Str(
        required=True,
        validate=ANONCREDS_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation Registry identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
    )
