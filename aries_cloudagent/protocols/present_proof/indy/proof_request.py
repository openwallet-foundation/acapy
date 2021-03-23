"""Utilities to deal with indy."""

from marshmallow import fields, validate, validates_schema, ValidationError

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    INDY_CRED_DEF_ID,
    INDY_DID,
    INDY_PREDICATE,
    INDY_SCHEMA_ID,
    INDY_VERSION,
    INT_EPOCH,
)


class IndyProofReqPredSpecRestrictionsSchema(OpenAPISchema):
    """Schema for restrictions in attr or pred specifier indy proof request."""

    schema_id = fields.String(
        description="Schema identifier", required=False, **INDY_SCHEMA_ID
    )
    schema_issuer_did = fields.String(
        description="Schema issuer (origin) DID", required=False, **INDY_DID
    )
    schema_name = fields.String(
        example="transcript", description="Schema name", required=False
    )
    schema_version = fields.String(
        description="Schema version", required=False, **INDY_VERSION
    )
    issuer_did = fields.String(
        description="Credential issuer DID", required=False, **INDY_DID
    )
    cred_def_id = fields.String(
        description="Credential definition identifier",
        required=False,
        **INDY_CRED_DEF_ID,
    )


class IndyProofReqNonRevokedSchema(OpenAPISchema):
    """Non-revocation times specification in indy proof request."""

    to = fields.Int(
        description="Timestamp of interest for non-revocation proof",
        required=True,
        strict=True,
        **INT_EPOCH,
    )


class IndyProofReqAttrSpecSchema(OpenAPISchema):
    """Schema for attribute specification in indy proof request."""

    name = fields.String(
        example="favouriteDrink", description="Attribute name", required=False
    )
    names = fields.List(
        fields.String(example="age"),
        description="Attribute name group",
        required=False,
    )
    restrictions = fields.List(
        fields.Dict(
            keys=fields.Str(
                validate=validate.Regexp(
                    "^schema_id|"
                    "schema_issuer_did|"
                    "schema_name|"
                    "schema_version|"
                    "issuer_did|"
                    "cred_def_id|"
                    "attr::.+::value$"  # indy does not support attr::...::marker here
                ),
                example="cred_def_id",  # marshmallow/apispec v3.0 ignores
            ),
            values=fields.Str(example=INDY_CRED_DEF_ID["example"]),
        ),
        description=(
            "If present, credential must satisfy one of given restrictions: specify "
            "schema_id, schema_issuer_did, schema_name, schema_version, "
            "issuer_did, cred_def_id, and/or attr::<attribute-name>::value "
            "where <attribute-name> represents a credential attribute name"
        ),
        required=False,
    )
    non_revoked = fields.Nested(
        IndyProofReqNonRevokedSchema(),
        required=False,
        allow_none=True,  # accommodate libvcx
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """
        Validate schema fields.

        Data must have exactly one of name or names; if names then restrictions are
        mandatory.

        Args:
            data: The data to validate

        Raises:
            ValidationError: if data has both or neither of name and names

        """
        if ("name" in data) == ("names" in data):
            raise ValidationError(
                "Attribute specification must have either name or names but not both"
            )
        restrictions = data.get("restrictions")
        if ("names" in data) and (not restrictions or all(not r for r in restrictions)):
            raise ValidationError(
                "Attribute specification on 'names' must have non-empty restrictions"
            )


class IndyProofReqPredSpecSchema(OpenAPISchema):
    """Schema for predicate specification in indy proof request."""

    name = fields.String(example="index", description="Attribute name", required=True)
    p_type = fields.String(
        description="Predicate type ('<', '<=', '>=', or '>')",
        required=True,
        **INDY_PREDICATE,
    )
    p_value = fields.Int(description="Threshold value", required=True, strict=True)
    restrictions = fields.List(
        fields.Nested(IndyProofReqPredSpecRestrictionsSchema()),
        description="If present, credential must satisfy one of given restrictions",
        required=False,
    )
    non_revoked = fields.Nested(
        IndyProofReqNonRevokedSchema(),
        required=False,
        allow_none=True,  # accommodate libvcx
    )


class IndyProofRequestSchema(OpenAPISchema):
    """Schema for indy proof request."""

    nonce = fields.String(description="Nonce", required=False, example="1234567890")
    name = fields.String(
        description="Proof request name",
        required=False,
        example="Proof request",
        default="Proof request",
    )
    version = fields.String(
        description="Proof request version",
        required=False,
        default="1.0",
        **INDY_VERSION,
    )
    requested_attributes = fields.Dict(
        description="Requested attribute specifications of proof request",
        required=True,
        keys=fields.Str(example="0_attr_uuid"),  # marshmallow/apispec v3.0 ignores
        values=fields.Nested(IndyProofReqAttrSpecSchema()),
    )
    requested_predicates = fields.Dict(
        description="Requested predicate specifications of proof request",
        required=True,
        keys=fields.Str(example="0_age_GE_uuid"),  # marshmallow/apispec v3.0 ignores
        values=fields.Nested(IndyProofReqPredSpecSchema()),
    )
    non_revoked = fields.Nested(
        IndyProofReqNonRevokedSchema(),
        required=False,
        allow_none=True,  # accommodate libvcx
    )
