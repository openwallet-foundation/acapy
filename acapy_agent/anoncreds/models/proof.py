"""Marshmallow bindings for anoncreds proofs."""

from typing import Mapping, Optional, Sequence

from marshmallow import EXCLUDE, fields, validate

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    ANONCREDS_CRED_DEF_ID_VALIDATE,
    ANONCREDS_REV_REG_ID_EXAMPLE,
    ANONCREDS_REV_REG_ID_VALIDATE,
    ANONCREDS_SCHEMA_ID_EXAMPLE,
    ANONCREDS_SCHEMA_ID_VALIDATE,
    INT_EPOCH_EXAMPLE,
    INT_EPOCH_VALIDATE,
    NUM_STR_ANY_EXAMPLE,
    NUM_STR_ANY_VALIDATE,
    NUM_STR_WHOLE_EXAMPLE,
    NUM_STR_WHOLE_VALIDATE,
)
from ...utils.tracing import AdminAPIMessageTracingSchema
from .predicate import Predicate
from .requested_credentials import (
    AnonCredsRequestedCredsRequestedAttrSchema,
    AnonCredsRequestedCredsRequestedPredSchema,
)


class AnonCredsEQProof(BaseModel):
    """Equality proof for anoncreds primary proof."""

    class Meta:
        """Equality proof metadata."""

        schema_class = "AnonCredsEQProofMeta"

    def __init__(
        self,
        revealed_attrs: Mapping[str, str] = None,
        a_prime: Optional[str] = None,
        e: Optional[str] = None,
        v: Optional[str] = None,
        m: Mapping[str, str] = None,
        m2: Optional[str] = None,
        **kwargs,
    ):
        """Initialize equality proof object."""
        super().__init__(**kwargs)
        self.revealed_attrs = revealed_attrs
        self.a_prime = a_prime
        self.e = e
        self.v = v
        self.m = m
        self.m2 = m2


class AnonCredsEQProofSchema(BaseModelSchema):
    """AnonCreds equality proof schema."""

    class Meta:
        """AnonCreds equality proof metadata."""

        model_class = AnonCredsEQProof
        unknown = EXCLUDE

    revealed_attrs = fields.Dict(
        keys=fields.Str(metadata={"example": "preference"}),
        values=fields.Str(
            validate=NUM_STR_ANY_VALIDATE, metadata={"example": NUM_STR_ANY_EXAMPLE}
        ),
    )
    a_prime = fields.Str(
        validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
    )
    e = fields.Str(
        validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
    )
    v = fields.Str(
        validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
    )
    m = fields.Dict(
        keys=fields.Str(metadata={"example": "master_secret"}),
        values=fields.Str(
            validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
        ),
    )
    m2 = fields.Str(
        validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
    )


class AnonCredsGEProofPred(BaseModel):
    """AnonCreds GE proof predicate."""

    class Meta:
        """AnonCreds GE proof predicate metadata."""

        schema_class = "AnonCredsGEProofPredSchema"

    def __init__(
        self,
        attr_name: Optional[str] = None,
        p_type: Optional[str] = None,
        value: Optional[int] = None,
        **kwargs,
    ):
        """Initialize anoncreds GE proof predicate."""
        super().__init__(**kwargs)
        self.attr_name = attr_name
        self.p_type = p_type
        self.value = value


class AnonCredsGEProofPredSchema(BaseModelSchema):
    """AnonCreds GE proof predicate schema."""

    class Meta:
        """AnonCreds GE proof predicate metadata."""

        model_class = AnonCredsGEProofPred
        unknown = EXCLUDE

    attr_name = fields.Str(
        metadata={"description": "Attribute name, anoncreds-canonicalized"}
    )
    p_type = fields.Str(
        validate=validate.OneOf([p.fortran for p in Predicate]),
        metadata={"description": "Predicate type"},
    )
    value = fields.Integer(
        metadata={"strict": True, "description": "Predicate threshold value"}
    )


class AnonCredsGEProof(BaseModel):
    """Greater-than-or-equal-to proof for anoncreds primary proof."""

    class Meta:
        """GE proof metadata."""

        schema_class = "AnonCredsGEProofMeta"

    def __init__(
        self,
        u: Mapping[str, str] = None,
        r: Mapping[str, str] = None,
        mj: Optional[str] = None,
        alpha: Optional[str] = None,
        t: Mapping[str, str] = None,
        predicate: Optional[AnonCredsGEProofPred] = None,
        **kwargs,
    ):
        """Initialize GE proof object."""
        super().__init__(**kwargs)
        self.u = u
        self.r = r
        self.mj = mj
        self.alpha = alpha
        self.t = t
        self.predicate = predicate


class AnonCredsGEProofSchema(BaseModelSchema):
    """AnonCreds GE proof schema."""

    class Meta:
        """AnonCreds GE proof schema metadata."""

        model_class = AnonCredsGEProof
        unknown = EXCLUDE

    u = fields.Dict(
        keys=fields.Str(),
        values=fields.Str(
            validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
        ),
    )
    r = fields.Dict(
        keys=fields.Str(),
        values=fields.Str(
            validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
        ),
    )
    mj = fields.Str(
        validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
    )
    alpha = fields.Str(
        validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
    )
    t = fields.Dict(
        keys=fields.Str(),
        values=fields.Str(
            validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
        ),
    )
    predicate = fields.Nested(AnonCredsGEProofPredSchema)


class AnonCredsPrimaryProof(BaseModel):
    """AnonCreds primary proof."""

    class Meta:
        """AnonCreds primary proof metadata."""

        schema_class = "AnonCredsPrimaryProofSchema"

    def __init__(
        self,
        eq_proof: Optional[AnonCredsEQProof] = None,
        ge_proofs: Sequence[AnonCredsGEProof] = None,
        **kwargs,
    ):
        """Initialize anoncreds primary proof."""
        super().__init__(**kwargs)
        self.eq_proof = eq_proof
        self.ge_proofs = ge_proofs


class AnonCredsPrimaryProofSchema(BaseModelSchema):
    """AnonCreds primary proof schema."""

    class Meta:
        """AnonCreds primary proof schema metadata."""

        model_class = AnonCredsPrimaryProof
        unknown = EXCLUDE

    eq_proof = fields.Nested(
        AnonCredsEQProofSchema,
        allow_none=True,
        metadata={"description": "AnonCreds equality proof"},
    )
    ge_proofs = fields.Nested(
        AnonCredsGEProofSchema,
        many=True,
        allow_none=True,
        metadata={"description": "AnonCreds GE proofs"},
    )


class AnonCredsNonRevocProof(BaseModel):
    """AnonCreds non-revocation proof."""

    class Meta:
        """AnonCreds non-revocation proof metadata."""

        schema_class = "AnonCredsNonRevocProofSchema"

    def __init__(
        self,
        x_list: Optional[Mapping] = None,
        c_list: Optional[Mapping] = None,
        **kwargs,
    ):
        """Initialize anoncreds non-revocation proof."""
        super().__init__(**kwargs)
        self.x_list = x_list
        self.c_list = c_list


class AnonCredsNonRevocProofSchema(BaseModelSchema):
    """AnonCreds non-revocation proof schema."""

    class Meta:
        """AnonCreds non-revocation proof schema metadata."""

        model_class = AnonCredsNonRevocProof
        unknown = EXCLUDE

    x_list = fields.Dict(keys=fields.Str(), values=fields.Str())
    c_list = fields.Dict(keys=fields.Str(), values=fields.Str())


class AnonCredsProofProofProofsProof(BaseModel):
    """AnonCreds proof.proof.proofs constituent proof."""

    class Meta:
        """AnonCreds proof.proof.proofs constituent proof schema."""

        schema_class = "AnonCredsProofProofProofsProofSchema"

    def __init__(
        self,
        primary_proof: Optional[AnonCredsPrimaryProof] = None,
        non_revoc_proof: Optional[AnonCredsNonRevocProof] = None,
        **kwargs,
    ):
        """Initialize proof.proof.proofs constituent proof."""
        super().__init__(**kwargs)
        self.primary_proof = primary_proof
        self.non_revoc_proof = non_revoc_proof


class AnonCredsProofProofProofsProofSchema(BaseModelSchema):
    """AnonCreds proof.proof.proofs constituent proof schema."""

    class Meta:
        """AnonCreds proof.proof.proofs constituent proof schema metadata."""

        model_class = AnonCredsProofProofProofsProof
        unknown = EXCLUDE

    primary_proof = fields.Nested(
        AnonCredsPrimaryProofSchema, metadata={"description": "AnonCreds primary proof"}
    )
    non_revoc_proof = fields.Nested(
        AnonCredsNonRevocProofSchema,
        allow_none=True,
        metadata={"description": "AnonCreds non-revocation proof"},
    )


class AnonCredsProofProofAggregatedProof(BaseModel):
    """AnonCreds proof.proof aggregated proof."""

    class Meta:
        """AnonCreds proof.proof aggregated proof metadata."""

        schema_class = "AnonCredsProofProofAggregatedProofSchema"

    def __init__(
        self,
        c_hash: Optional[str] = None,
        c_list: Sequence[Sequence[int]] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof.proof agreggated proof."""
        super().__init__(**kwargs)
        self.c_hash = c_hash
        self.c_list = c_list


class AnonCredsProofProofAggregatedProofSchema(BaseModelSchema):
    """AnonCreds proof.proof aggregated proof schema."""

    class Meta:
        """AnonCreds proof.proof aggregated proof schema metadata."""

        model_class = AnonCredsProofProofAggregatedProof
        unknown = EXCLUDE

    c_hash = fields.Str(metadata={"description": "c_hash value"})
    c_list = fields.List(
        fields.List(fields.Int(metadata={"strict": True})),
        metadata={"description": "c_list value"},
    )


class AnonCredsProofProof(BaseModel):
    """AnonCreds proof.proof content."""

    class Meta:
        """AnonCreds proof.proof content metadata."""

        schema_class = "AnonCredsProofProofSchema"

    def __init__(
        self,
        proofs: Sequence[AnonCredsProofProofProofsProof] = None,
        aggregated_proof: Optional[AnonCredsProofProofAggregatedProof] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof.proof content."""
        super().__init__(**kwargs)
        self.proofs = proofs
        self.aggregated_proof = aggregated_proof


class AnonCredsProofProofSchema(BaseModelSchema):
    """AnonCreds proof.proof content schema."""

    class Meta:
        """AnonCreds proof.proof content schema metadata."""

        model_class = AnonCredsProofProof
        unknown = EXCLUDE

    proofs = fields.Nested(
        AnonCredsProofProofProofsProofSchema,
        many=True,
        metadata={"description": "AnonCreds proof proofs"},
    )
    aggregated_proof = fields.Nested(
        AnonCredsProofProofAggregatedProofSchema,
        metadata={"description": "AnonCreds proof aggregated proof"},
    )


class RawEncoded(BaseModel):
    """Raw and encoded attribute values."""

    class Meta:
        """Raw and encoded attribute values metadata."""

        schema_class = "RawEncodedSchema"

    def __init__(
        self,
        raw: Optional[str] = None,
        encoded: Optional[str] = None,
        **kwargs,
    ):
        """Initialize raw and encoded attribute values."""
        super().__init__(**kwargs)
        self.raw = raw
        self.encoded = encoded


class RawEncodedSchema(BaseModelSchema):
    """Raw and encoded attribute values schema."""

    class Meta:
        """Raw and encoded attribute values schema metadata."""

        model_class = RawEncoded
        unknown = EXCLUDE

    raw = fields.Str(metadata={"description": "Raw value"})
    encoded = fields.Str(
        validate=NUM_STR_ANY_VALIDATE,
        metadata={"description": "Encoded value", "example": NUM_STR_ANY_EXAMPLE},
    )


class AnonCredsProofRequestedProofRevealedAttr(RawEncoded):
    """AnonCreds proof requested proof revealed attr."""

    class Meta:
        """AnonCreds proof requested proof revealed attr metadata."""

        schema_class = "AnonCredsProofRequestedProofRevealedAttrSchema"

    def __init__(
        self,
        sub_proof_index: Optional[int] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof requested proof revealed attr."""
        super().__init__(**kwargs)
        self.sub_proof_index = sub_proof_index


class AnonCredsProofRequestedProofRevealedAttrSchema(RawEncodedSchema):
    """AnonCreds proof requested proof revealed attr schema."""

    class Meta:
        """AnonCreds proof requested proof revealed attr schema metadata."""

        model_class = AnonCredsProofRequestedProofRevealedAttr
        unknown = EXCLUDE

    sub_proof_index = fields.Int(
        metadata={"strict": True, "description": "Sub-proof index"}
    )


class AnonCredsProofRequestedProofRevealedAttrGroup(BaseModel):
    """AnonCreds proof requested proof revealed attr group."""

    class Meta:
        """AnonCreds proof requested proof revealed attr group metadata."""

        schema_class = "AnonCredsProofRequestedProofRevealedAttrGroupSchema"

    def __init__(
        self,
        sub_proof_index: Optional[int] = None,
        values: Mapping[str, RawEncoded] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof requested proof revealed attr."""
        super().__init__(**kwargs)
        self.sub_proof_index = sub_proof_index
        self.values = values


class AnonCredsProofRequestedProofRevealedAttrGroupSchema(BaseModelSchema):
    """AnonCreds proof requested proof revealed attr group schema."""

    class Meta:
        """AnonCreds proof requested proof revealed attr group schema metadata."""

        model_class = AnonCredsProofRequestedProofRevealedAttrGroup
        unknown = EXCLUDE

    sub_proof_index = fields.Int(
        metadata={"strict": True, "description": "Sub-proof index"}
    )
    values = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(RawEncodedSchema),
        metadata={
            "description": "AnonCreds proof requested proof revealed attr groups group value"  # noqa: E501
        },
    )


class AnonCredsProofRequestedProofPredicate(BaseModel):
    """AnonCreds proof requested proof predicate."""

    class Meta:
        """AnonCreds proof requested proof requested proof predicate metadata."""

        schema_class = "AnonCredsProofRequestedProofPredicateSchema"

    def __init__(
        self,
        sub_proof_index: Optional[int] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof requested proof predicate."""
        super().__init__(**kwargs)
        self.sub_proof_index = sub_proof_index


class AnonCredsProofRequestedProofPredicateSchema(BaseModelSchema):
    """AnonCreds proof requested prrof predicate schema."""

    class Meta:
        """AnonCreds proof requested proof requested proof predicate schema metadata."""

        model_class = AnonCredsProofRequestedProofPredicate
        unknown = EXCLUDE

    sub_proof_index = fields.Int(
        metadata={"strict": True, "description": "Sub-proof index"}
    )


class AnonCredsProofRequestedProof(BaseModel):
    """AnonCreds proof.requested_proof content."""

    class Meta:
        """AnonCreds proof.requested_proof content metadata."""

        schema_class = "AnonCredsProofRequestedProofSchema"

    def __init__(
        self,
        revealed_attrs: Mapping[str, AnonCredsProofRequestedProofRevealedAttr] = None,
        revealed_attr_groups: Mapping[
            str,
            AnonCredsProofRequestedProofRevealedAttrGroup,
        ] = None,
        self_attested_attrs: Optional[Mapping] = None,
        unrevealed_attrs: Optional[Mapping] = None,
        predicates: Mapping[str, AnonCredsProofRequestedProofPredicate] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof requested proof."""
        super().__init__(**kwargs)
        self.revealed_attrs = revealed_attrs
        self.revealed_attr_groups = revealed_attr_groups
        self.self_attested_attrs = self_attested_attrs
        self.unrevealed_attrs = unrevealed_attrs
        self.predicates = predicates


class AnonCredsProofRequestedProofSchema(BaseModelSchema):
    """AnonCreds proof requested proof schema."""

    class Meta:
        """AnonCreds proof requested proof schema metadata."""

        model_class = AnonCredsProofRequestedProof
        unknown = EXCLUDE

    revealed_attrs = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(AnonCredsProofRequestedProofRevealedAttrSchema),
        allow_none=True,
        metadata={"description": "Proof requested proof revealed attributes"},
    )
    revealed_attr_groups = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(AnonCredsProofRequestedProofRevealedAttrGroupSchema),
        allow_none=True,
        metadata={"description": "Proof requested proof revealed attribute groups"},
    )
    self_attested_attrs = fields.Dict(
        metadata={"description": "Proof requested proof self-attested attributes"}
    )
    unrevealed_attrs = fields.Dict(metadata={"description": "Unrevealed attributes"})
    predicates = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(AnonCredsProofRequestedProofPredicateSchema),
        metadata={"description": "Proof requested proof predicates."},
    )


class AnonCredsProofIdentifier(BaseModel):
    """AnonCreds proof identifier."""

    class Meta:
        """AnonCreds proof identifier metadata."""

        schema_class = "AnonCredsProofIdentifierSchema"

    def __init__(
        self,
        schema_id: Optional[str] = None,
        cred_def_id: Optional[str] = None,
        rev_reg_id: Optional[str] = None,
        timestamp: Optional[int] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof identifier."""
        super().__init__(**kwargs)
        self.schema_id = schema_id
        self.cred_def_id = cred_def_id
        self.rev_reg_id = rev_reg_id
        self.timestamp = timestamp


class AnonCredsProofIdentifierSchema(BaseModelSchema):
    """AnonCreds proof identifier schema."""

    class Meta:
        """AnonCreds proof identifier schema metadata."""

        model_class = AnonCredsProofIdentifier
        unknown = EXCLUDE

    schema_id = fields.Str(
        validate=ANONCREDS_SCHEMA_ID_VALIDATE,
        metadata={
            "description": "Schema identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        },
    )
    cred_def_id = fields.Str(
        validate=ANONCREDS_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
        },
    )
    rev_reg_id = fields.Str(
        allow_none=True,
        validate=ANONCREDS_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation registry identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
    )
    timestamp = fields.Int(
        allow_none=True,
        validate=INT_EPOCH_VALIDATE,
        metadata={
            "strict": True,
            "description": "Timestamp epoch",
            "example": INT_EPOCH_EXAMPLE,
        },
    )


class AnonCredsProof(BaseModel):
    """AnonCreds proof."""

    class Meta:
        """AnonCreds proof metadata."""

        schema_class = "AnonCredsProofSchema"

    def __init__(
        self,
        proof: Optional[AnonCredsProofProof] = None,
        requested_proof: Optional[AnonCredsProofRequestedProof] = None,
        identifiers: Sequence[AnonCredsProofIdentifier] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof."""
        super().__init__(**kwargs)
        self.proof = proof
        self.requested_proof = requested_proof
        self.identifiers = identifiers


class AnonCredsProofSchema(BaseModelSchema):
    """AnonCreds proof schema."""

    class Meta:
        """AnonCreds proof schema metadata."""

        model_class = AnonCredsProof
        unknown = EXCLUDE

    proof = fields.Nested(
        AnonCredsProofProofSchema,
        metadata={"description": "AnonCreds proof.proof content"},
    )
    requested_proof = fields.Nested(
        AnonCredsProofRequestedProofSchema,
        metadata={"description": "AnonCreds proof.requested_proof content"},
    )
    identifiers = fields.Nested(
        AnonCredsProofIdentifierSchema,
        many=True,
        metadata={"description": "AnonCreds proof.identifiers content"},
    )


class AnonCredsPresSpecSchema(AdminAPIMessageTracingSchema):
    """Request schema for anoncreds proof specification to send as presentation."""

    self_attested_attributes = fields.Dict(
        required=True,
        keys=fields.Str(metadata={"example": "attr_name"}),
        values=fields.Str(
            metadata={
                "example": "self_attested_value",
                "description": (
                    "Self-attested attribute values to use in requested-credentials"
                    " structure for proof construction"
                ),
            }
        ),
        metadata={"description": "Self-attested attributes to build into proof"},
    )
    requested_attributes = fields.Dict(
        required=True,
        keys=fields.Str(metadata={"example": "attr_referent"}),
        values=fields.Nested(AnonCredsRequestedCredsRequestedAttrSchema),
        metadata={
            "description": (
                "Nested object mapping proof request attribute referents to"
                " requested-attribute specifiers"
            )
        },
    )
    requested_predicates = fields.Dict(
        required=True,
        keys=fields.Str(metadata={"example": "pred_referent"}),
        values=fields.Nested(AnonCredsRequestedCredsRequestedPredSchema),
        metadata={
            "description": (
                "Nested object mapping proof request predicate referents to"
                " requested-predicate specifiers"
            )
        },
    )
    trace = fields.Bool(
        required=False,
        metadata={
            "description": "Whether to trace event (default false)",
            "example": False,
        },
    )
