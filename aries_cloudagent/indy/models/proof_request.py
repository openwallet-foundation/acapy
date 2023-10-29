"""Utilities to deal with indy."""

from typing import Mapping

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
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_PREDICATE_EXAMPLE,
    INDY_PREDICATE_VALIDATE,
    INDY_VERSION_EXAMPLE,
    INDY_VERSION_VALIDATE,
    INT_EPOCH_EXAMPLE,
    INT_EPOCH_VALIDATE,
    NUM_STR_NATURAL_EXAMPLE,
    NUM_STR_NATURAL_VALIDATE,
)


class IndyProofReqAttrSpecSchema(OpenAPISchema):
    """Schema for attribute specification in indy proof request."""

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
            values=fields.Str(metadata={"example": INDY_CRED_DEF_ID_EXAMPLE}),
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
            name="IndyProofReqAttrSpecNonRevokedSchema",
        ),
        allow_none=True,
        required=False,
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

    name = fields.Str(
        required=True, metadata={"example": "index", "description": "Attribute name"}
    )
    p_type = fields.Str(
        required=True,
        validate=INDY_PREDICATE_VALIDATE,
        metadata={
            "description": "Predicate type ('<', '<=', '>=', or '>')",
            "example": INDY_PREDICATE_EXAMPLE,
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
            values=fields.Str(metadata={"example": INDY_CRED_DEF_ID_EXAMPLE}),
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
            name="IndyProofReqPredSpecNonRevokedSchema",
        ),
        allow_none=True,
        required=False,
    )


class IndyProofRequest(BaseModel):
    """Indy proof request."""

    class Meta:
        """Indy proof request metadata."""

        schema_class = "IndyProofRequestSchema"

    def __init__(
        self,
        nonce: str = None,
        name: str = None,
        version: str = None,
        requested_attributes: Mapping = None,
        requested_predicates: Mapping = None,
        non_revoked: Mapping = None,
        **kwargs,
    ):
        """
        Initialize indy cred abstract object.

        Args:
            schema_id: schema identifier
            cred_def_id: credential definition identifier
            nonce: nonce
            key_correctness_proof: key correctness proof

        """
        super().__init__(**kwargs)
        self.nonce = nonce
        self.name = name
        self.version = version
        self.requested_attributes = requested_attributes
        self.requested_predicates = requested_predicates
        self.non_revoked = non_revoked


class IndyProofRequestSchema(BaseModelSchema):
    """Schema for indy proof request."""

    class Meta:
        """Indy proof request schema metadata."""

        model_class = IndyProofRequest
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
        validate=INDY_VERSION_VALIDATE,
        metadata={
            "description": "Proof request version",
            "example": INDY_VERSION_EXAMPLE,
        },
    )
    requested_attributes = fields.Dict(
        required=True,
        keys=fields.Str(
            metadata={"decription": "Attribute referent", "example": "0_legalname_uuid"}
        ),
        values=fields.Nested(IndyProofReqAttrSpecSchema()),
        metadata={"description": "Requested attribute specifications of proof request"},
    )
    requested_predicates = fields.Dict(
        required=True,
        keys=fields.Str(
            metadata={"description": "Predicate referent", "example": "0_age_GE_uuid"}
        ),
        values=fields.Nested(IndyProofReqPredSpecSchema()),
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
            name="IndyProofRequestNonRevokedSchema",
        ),
        allow_none=True,
        required=False,
    )
