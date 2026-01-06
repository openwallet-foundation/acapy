"""AnonCreds revocation registry models."""

from marshmallow import ValidationError, fields, validate, validates_schema

from .....messaging.models.openapi import OpenAPISchema
from .....messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    ANONCREDS_CRED_DEF_ID_VALIDATE,
    ANONCREDS_DID_EXAMPLE,
    ANONCREDS_REV_REG_ID_EXAMPLE,
    ANONCREDS_REV_REG_ID_VALIDATE,
    ANONCREDS_SCHEMA_ID_EXAMPLE,
    UUID4_EXAMPLE,
    UUID4_VALIDATE,
    WHOLE_NUM_EXAMPLE,
    WHOLE_NUM_VALIDATE,
)
from .....revocation.models.issuer_rev_reg_record import (
    IssuerRevRegRecordSchema,
)
from ....models.issuer_cred_rev_record import (
    IssuerCredRevRecordSchemaAnonCreds,
)
from ....models.revocation import RevRegDefState
from ...common.schemas import (
    CredRevRecordQueryStringMixin,
    EndorserOptionsSchema,
    RevocationIdsDictMixin,
    RevRegIdMatchInfoMixin,
)


class AnonCredsRevRegIdMatchInfoSchema(RevRegIdMatchInfoMixin):
    """Path parameters and validators for request taking rev reg id."""

    pass


class InnerRevRegDefSchema(OpenAPISchema):
    """Request schema for revocation registry creation request."""

    issuer_id = fields.Str(
        metadata={
            "description": "Issuer Identifier of the credential definition or schema",
            "example": ANONCREDS_DID_EXAMPLE,
        },
        data_key="issuerId",
        required=True,
    )
    cred_def_id = fields.Str(
        metadata={
            "description": "Credential definition identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        },
        data_key="credDefId",
        required=True,
    )
    tag = fields.Str(
        metadata={"description": "tag for revocation registry", "example": "default"},
        required=True,
    )
    max_cred_num = fields.Int(
        metadata={
            "description": "Maximum number of credential revocations per registry",
            "example": 777,
        },
        data_key="maxCredNum",
        required=True,
    )


class RevRegDefOptionsSchema(EndorserOptionsSchema):
    """Parameters and validators for rev reg def options."""

    pass


class RevRegCreateRequestSchemaAnonCreds(OpenAPISchema):
    """Wrapper for revocation registry creation request."""

    revocation_registry_definition = fields.Nested(InnerRevRegDefSchema())
    options = fields.Nested(RevRegDefOptionsSchema())


class RevRegResultSchemaAnonCreds(OpenAPISchema):
    """Result schema for revocation registry creation request."""

    result = fields.Nested(IssuerRevRegRecordSchema())


class CredRevRecordQueryStringSchema(CredRevRecordQueryStringMixin):
    """Parameters and validators for credential revocation record request."""

    pass


class RevRegId(OpenAPISchema):
    """Parameters and validators for delete tails file request."""

    @validates_schema
    def validate_fields(self, data: dict, **kwargs) -> None:
        """Validate schema fields - must have either rr-id or cr-id."""
        rev_reg_id = data.get("rev_reg_id")
        cred_def_id = data.get("cred_def_id")

        if not (rev_reg_id or cred_def_id):
            raise ValidationError("Request must have either rev_reg_id or cred_def_id")

    rev_reg_id = fields.Str(
        required=False,
        validate=ANONCREDS_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation registry identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
    )
    cred_def_id = fields.Str(
        required=False,
        validate=ANONCREDS_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
        },
    )


class CredRevRecordResultSchemaAnonCreds(OpenAPISchema):
    """Result schema for credential revocation record request."""

    result = fields.Nested(IssuerCredRevRecordSchemaAnonCreds())


class CredRevRecordDetailsResultSchemaAnonCreds(OpenAPISchema):
    """Result schema for credential revocation record request."""

    results = fields.List(fields.Nested(IssuerCredRevRecordSchemaAnonCreds()))


class CredRevRecordsResultSchemaAnonCreds(OpenAPISchema):
    """Result schema for revoc reg delta."""

    rev_reg_delta = fields.Dict(
        metadata={"description": "AnonCreds revocation registry delta"}
    )


class RevRegIssuedResultSchemaAnonCreds(OpenAPISchema):
    """Result schema for revocation registry credentials issued request."""

    result = fields.Int(
        validate=WHOLE_NUM_VALIDATE,
        metadata={
            "description": "Number of credentials issued against revocation registry",
            "strict": True,
            "example": WHOLE_NUM_EXAMPLE,
        },
    )


class RevRegUpdateRequestMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking rev reg id."""

    apply_ledger_update = fields.Bool(
        required=True,
        metadata={"description": "Apply updated accumulator transaction to ledger"},
    )


class RevRegWalletUpdatedResultSchemaAnonCreds(OpenAPISchema):
    """Number of wallet revocation entries status updated."""

    rev_reg_delta = fields.Dict(
        metadata={"description": "AnonCreds revocation registry delta"}
    )
    accum_calculated = fields.Dict(
        metadata={"description": "Calculated accumulator for phantom revocations"}
    )
    accum_fixed = fields.Dict(
        metadata={"description": "Applied ledger transaction to fix revocations"}
    )


class RevRegsCreatedSchemaAnonCreds(OpenAPISchema):
    """Result schema for request for revocation registries created."""

    rev_reg_ids = fields.List(
        fields.Str(
            validate=ANONCREDS_REV_REG_ID_VALIDATE,
            metadata={
                "description": "Revocation registry identifiers",
                "example": ANONCREDS_REV_REG_ID_EXAMPLE,
            },
        )
    )


class RevRegUpdateTailsFileUriSchema(OpenAPISchema):
    """Request schema for updating tails file URI."""

    tails_public_uri = fields.Url(
        required=True,
        metadata={
            "description": "Public URI to the tails file",
            "example": (
                "http://192.168.56.133:6543/revocation/registry/"
                f"{ANONCREDS_REV_REG_ID_EXAMPLE}/tails-file"
            ),
        },
    )


class RevRegsCreatedQueryStringSchema(OpenAPISchema):
    """Query string parameters and validators for rev regs created request."""

    cred_def_id = fields.Str(
        required=False,
        validate=ANONCREDS_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
        },
    )
    state = fields.Str(
        required=False,
        validate=validate.OneOf(
            [
                getattr(RevRegDefState, m)
                for m in vars(RevRegDefState)
                if m.startswith("STATE_")
            ]
        ),
        metadata={"description": "Revocation registry state"},
    )


class SetRevRegStateQueryStringSchema(OpenAPISchema):
    """Query string parameters and validators for request to set rev reg state."""

    state = fields.Str(
        required=True,
        validate=validate.OneOf(
            [
                getattr(RevRegDefState, m)
                for m in vars(RevRegDefState)
                if m.startswith("STATE_")
            ]
        ),
        metadata={"description": "Revocation registry state to set"},
    )


class RevocationCredDefIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking cred def id."""

    cred_def_id = fields.Str(
        required=True,
        validate=ANONCREDS_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
        },
    )


class CreateRevRegTxnForEndorserOptionSchema(OpenAPISchema):
    """Class for user to input whether to create a transaction for endorser or not."""

    create_transaction_for_endorser = fields.Boolean(
        required=False,
        metadata={"description": "Create Transaction For Endorser's signature"},
    )


class RevRegConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        required=False,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )


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
