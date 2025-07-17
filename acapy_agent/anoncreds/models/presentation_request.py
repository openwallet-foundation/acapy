"""Classes to represent anoncreds presentation request."""

from typing import Mapping, Optional

from marshmallow import (
    EXCLUDE,
    Schema,
    ValidationError,
    fields,
    validate,
    validates_schema,
)

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    INT_EPOCH_EXAMPLE,
    INT_EPOCH_VALIDATE,
    MAJOR_MINOR_VERSION_EXAMPLE,
    MAJOR_MINOR_VERSION_VALIDATE,
    NUM_STR_NATURAL_EXAMPLE,
    NUM_STR_NATURAL_VALIDATE,
    PREDICATE_EXAMPLE,
    PREDICATE_VALIDATE,
)


class AnonCredsPresentationReqPredSpecSchema(OpenAPISchema):
    """Schema for predicate specification in anoncreds proof request."""

    name = fields.Str(
        required=True, metadata={"example": "index", "description": "Attribute name"}
    )
    p_type = fields.Str(
        required=True,
        validate=PREDICATE_VALIDATE,
        metadata={
            "description": "Predicate type ('<', '<=', '>=', or '>')",
            "example": PREDICATE_EXAMPLE,
        },
    )
    p_value = fields.Int(
        required=True, metadata={"description": "Threshold value", "strict": True}
    )
    restrictions = fields.List(
        fields.Dict(
            keys=fields.Str(
                validate=validate.Regexp(
                    "^schema_id|schema_issuer_did|schema_name|schema_version|issuer_did|"
                    "cred_def_id|attr::.+::value$"
                ),
                metadata={"example": "cred_def_id"},
            ),
            values=fields.Str(metadata={"example": ANONCREDS_CRED_DEF_ID_EXAMPLE}),
        ),
        required=False,
        metadata={
            "description": (
                "If present, credential must satisfy one of given restrictions: specify"
                " schema_id, schema_issuer_did, schema_name, schema_version,"
                " issuer_did, cred_def_id, and/or attr::<attribute-name>::value where"
                " <attribute-name> represents a credential attribute name"
            )
        },
    )
    non_revoked = fields.Nested(
        Schema.from_dict(
            {
                "from": fields.Int(
                    required=False,
                    validate=INT_EPOCH_VALIDATE,
                    metadata={
                        "description": (
                            "Earliest time of interest in non-revocation interval"
                        ),
                        "strict": True,
                        "example": INT_EPOCH_EXAMPLE,
                    },
                ),
                "to": fields.Int(
                    required=False,
                    validate=INT_EPOCH_VALIDATE,
                    metadata={
                        "description": (
                            "Latest time of interest in non-revocation interval"
                        ),
                        "strict": True,
                        "example": INT_EPOCH_EXAMPLE,
                    },
                ),
            },
            name="AnonCredsPresentationReqPredSpecNonRevokedSchema",
        ),
        allow_none=True,
        required=False,
    )


class AnonCredsPresentationReqAttrSpecSchema(OpenAPISchema):
    """Schema for attribute specification in anoncreds proof request."""

    name = fields.Str(
        required=False,
        metadata={"example": "favouriteDrink", "description": "Attribute name"},
    )
    names = fields.List(
        fields.Str(metadata={"example": "age"}),
        required=False,
        metadata={"description": "Attribute name group"},
    )
    restrictions = fields.List(
        fields.Dict(
            keys=fields.Str(
                validate=validate.Regexp(
                    "^schema_id|schema_issuer_did|schema_name|schema_version|issuer_did|"
                    "cred_def_id|attr::.+::value$"
                ),
                metadata={"example": "cred_def_id"},
            ),
            values=fields.Str(metadata={"example": ANONCREDS_CRED_DEF_ID_EXAMPLE}),
        ),
        required=False,
        metadata={
            "description": (
                "If present, credential must satisfy one of given restrictions: specify"
                " schema_id, schema_issuer_did, schema_name, schema_version,"
                " issuer_did, cred_def_id, and/or attr::<attribute-name>::value where"
                " <attribute-name> represents a credential attribute name"
            )
        },
    )
    non_revoked = fields.Nested(
        Schema.from_dict(
            {
                "from": fields.Int(
                    required=False,
                    validate=INT_EPOCH_VALIDATE,
                    metadata={
                        "description": (
                            "Earliest time of interest in non-revocation interval"
                        ),
                        "strict": True,
                        "example": INT_EPOCH_EXAMPLE,
                    },
                ),
                "to": fields.Int(
                    required=False,
                    validate=INT_EPOCH_VALIDATE,
                    metadata={
                        "description": (
                            "Latest time of interest in non-revocation interval"
                        ),
                        "strict": True,
                        "example": INT_EPOCH_EXAMPLE,
                    },
                ),
            },
            name="AnonCredsPresentationReqAttrSpecNonRevokedSchema",
        ),
        allow_none=True,
        required=False,
    )

    @validates_schema
    def validate_fields(self, data: dict, **kwargs) -> None:
        """Validate schema fields.

        Data must have exactly one of name or names; if names then restrictions are
        mandatory.

        Args:
            data: The data to validate
            kwargs: Additional keyword arguments

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


class AnonCredsPresentationRequest(BaseModel):
    """anoncreds proof request."""

    class Meta:
        """AnonCreds proof request metadata."""

        schema_class = "AnonCredsPresentationRequestSchema"

    def __init__(
        self,
        nonce: Optional[str] = None,
        name: Optional[str] = None,
        version: Optional[str] = None,
        requested_attributes: Optional[Mapping] = None,
        requested_predicates: Optional[Mapping] = None,
        non_revoked: Optional[Mapping] = None,
        **kwargs,
    ):
        """Initialize anoncreds cred abstract object.

        Args:
            nonce (str): The nonce value.
            name (str): The name of the proof request.
            version (str): The version of the proof request.
            requested_attributes (Mapping): A mapping of attribute names to attribute
                constraints.
            requested_predicates (Mapping): A mapping of predicate names to predicate
                constraints.
            non_revoked (Mapping): A mapping of non-revocation timestamps.
            kwargs: Keyword arguments for BaseModel

        """
        super().__init__(**kwargs)
        self.nonce = nonce
        self.name = name
        self.version = version
        self.requested_attributes = requested_attributes
        self.requested_predicates = requested_predicates
        self.non_revoked = non_revoked


class AnonCredsPresentationRequestSchema(BaseModelSchema):
    """Schema for anoncreds proof request."""

    class Meta:
        """AnonCreds proof request schema metadata."""

        model_class = AnonCredsPresentationRequest
        unknown = EXCLUDE

    nonce = fields.Str(
        required=False,
        validate=NUM_STR_NATURAL_VALIDATE,
        metadata={"description": "Nonce", "example": NUM_STR_NATURAL_EXAMPLE},
    )
    name = fields.Str(
        required=False,
        dump_default="Proof request",
        metadata={"description": "Proof request name", "example": "Proof request"},
    )
    version = fields.Str(
        required=False,
        dump_default="1.0",
        validate=MAJOR_MINOR_VERSION_VALIDATE,
        metadata={
            "description": "Proof request version",
            "example": MAJOR_MINOR_VERSION_EXAMPLE,
        },
    )
    requested_attributes = fields.Dict(
        required=True,
        keys=fields.Str(
            metadata={"decription": "Attribute referent", "example": "0_legalname_uuid"}
        ),
        values=fields.Nested(AnonCredsPresentationReqAttrSpecSchema()),
        metadata={"description": "Requested attribute specifications of proof request"},
    )
    requested_predicates = fields.Dict(
        required=True,
        keys=fields.Str(
            metadata={"description": "Predicate referent", "example": "0_age_GE_uuid"}
        ),
        values=fields.Nested(AnonCredsPresentationReqPredSpecSchema()),
        metadata={"description": "Requested predicate specifications of proof request"},
    )
    non_revoked = fields.Nested(
        Schema.from_dict(
            {
                "from": fields.Int(
                    required=False,
                    validate=INT_EPOCH_VALIDATE,
                    metadata={
                        "description": (
                            "Earliest time of interest in non-revocation interval"
                        ),
                        "strict": True,
                        "example": INT_EPOCH_EXAMPLE,
                    },
                ),
                "to": fields.Int(
                    required=False,
                    validate=INT_EPOCH_VALIDATE,
                    metadata={
                        "description": (
                            "Latest time of interest in non-revocation interval"
                        ),
                        "strict": True,
                        "example": INT_EPOCH_EXAMPLE,
                    },
                ),
            },
            name="AnonCredsPresentationRequestNonRevokedSchema",
        ),
        allow_none=True,
        required=False,
    )
