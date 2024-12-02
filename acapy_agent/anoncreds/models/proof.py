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
    AnoncredsRequestedCredsRequestedAttrSchema,
    AnoncredsRequestedCredsRequestedPredSchema,
)


class AnoncredsEQProof(BaseModel):
    """Equality proof for anoncreds primary proof."""

    class Meta:
        """Equality proof metadata."""

        schema_class = "AnoncredsEQProofMeta"

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


class AnoncredsEQProofSchema(BaseModelSchema):
    """Anoncreds equality proof schema."""

    class Meta:
        """Anoncreds equality proof metadata."""

        model_class = AnoncredsEQProof
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


class AnoncredsGEProofPred(BaseModel):
    """Anoncreds GE proof predicate."""

    class Meta:
        """Anoncreds GE proof predicate metadata."""

        schema_class = "AnoncredsGEProofPredSchema"

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


class AnoncredsGEProofPredSchema(BaseModelSchema):
    """Anoncreds GE proof predicate schema."""

    class Meta:
        """Anoncreds GE proof predicate metadata."""

        model_class = AnoncredsGEProofPred
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


class AnoncredsGEProof(BaseModel):
    """Greater-than-or-equal-to proof for anoncreds primary proof."""

    class Meta:
        """GE proof metadata."""

        schema_class = "AnoncredsGEProofMeta"

    def __init__(
        self,
        u: Mapping[str, str] = None,
        r: Mapping[str, str] = None,
        mj: Optional[str] = None,
        alpha: Optional[str] = None,
        t: Mapping[str, str] = None,
        predicate: Optional[AnoncredsGEProofPred] = None,
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


class AnoncredsGEProofSchema(BaseModelSchema):
    """Anoncreds GE proof schema."""

    class Meta:
        """Anoncreds GE proof schema metadata."""

        model_class = AnoncredsGEProof
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
    predicate = fields.Nested(AnoncredsGEProofPredSchema)


class AnoncredsPrimaryProof(BaseModel):
    """Anoncreds primary proof."""

    class Meta:
        """Anoncreds primary proof metadata."""

        schema_class = "AnoncredsPrimaryProofSchema"

    def __init__(
        self,
        eq_proof: Optional[AnoncredsEQProof] = None,
        ge_proofs: Sequence[AnoncredsGEProof] = None,
        **kwargs,
    ):
        """Initialize anoncreds primary proof."""
        super().__init__(**kwargs)
        self.eq_proof = eq_proof
        self.ge_proofs = ge_proofs


class AnoncredsPrimaryProofSchema(BaseModelSchema):
    """Anoncreds primary proof schema."""

    class Meta:
        """Anoncreds primary proof schema metadata."""

        model_class = AnoncredsPrimaryProof
        unknown = EXCLUDE

    eq_proof = fields.Nested(
        AnoncredsEQProofSchema,
        allow_none=True,
        metadata={"description": "Anoncreds equality proof"},
    )
    ge_proofs = fields.Nested(
        AnoncredsGEProofSchema,
        many=True,
        allow_none=True,
        metadata={"description": "Anoncreds GE proofs"},
    )


class AnoncredsNonRevocProof(BaseModel):
    """Anoncreds non-revocation proof."""

    class Meta:
        """Anoncreds non-revocation proof metadata."""

        schema_class = "AnoncredsNonRevocProofSchema"

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


class AnoncredsNonRevocProofSchema(BaseModelSchema):
    """Anoncreds non-revocation proof schema."""

    class Meta:
        """Anoncreds non-revocation proof schema metadata."""

        model_class = AnoncredsNonRevocProof
        unknown = EXCLUDE

    x_list = fields.Dict(keys=fields.Str(), values=fields.Str())
    c_list = fields.Dict(keys=fields.Str(), values=fields.Str())


class AnoncredsProofProofProofsProof(BaseModel):
    """Anoncreds proof.proof.proofs constituent proof."""

    class Meta:
        """Anoncreds proof.proof.proofs constituent proof schema."""

        schema_class = "AnoncredsProofProofProofsProofSchema"

    def __init__(
        self,
        primary_proof: Optional[AnoncredsPrimaryProof] = None,
        non_revoc_proof: Optional[AnoncredsNonRevocProof] = None,
        **kwargs,
    ):
        """Initialize proof.proof.proofs constituent proof."""
        super().__init__(**kwargs)
        self.primary_proof = primary_proof
        self.non_revoc_proof = non_revoc_proof


class AnoncredsProofProofProofsProofSchema(BaseModelSchema):
    """Anoncreds proof.proof.proofs constituent proof schema."""

    class Meta:
        """Anoncreds proof.proof.proofs constituent proof schema metadata."""

        model_class = AnoncredsProofProofProofsProof
        unknown = EXCLUDE

    primary_proof = fields.Nested(
        AnoncredsPrimaryProofSchema, metadata={"description": "Anoncreds primary proof"}
    )
    non_revoc_proof = fields.Nested(
        AnoncredsNonRevocProofSchema,
        allow_none=True,
        metadata={"description": "Anoncreds non-revocation proof"},
    )


class AnoncredsProofProofAggregatedProof(BaseModel):
    """Anoncreds proof.proof aggregated proof."""

    class Meta:
        """Anoncreds proof.proof aggregated proof metadata."""

        schema_class = "AnoncredsProofProofAggregatedProofSchema"

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


class AnoncredsProofProofAggregatedProofSchema(BaseModelSchema):
    """Anoncreds proof.proof aggregated proof schema."""

    class Meta:
        """Anoncreds proof.proof aggregated proof schema metadata."""

        model_class = AnoncredsProofProofAggregatedProof
        unknown = EXCLUDE

    c_hash = fields.Str(metadata={"description": "c_hash value"})
    c_list = fields.List(
        fields.List(fields.Int(metadata={"strict": True})),
        metadata={"description": "c_list value"},
    )


class AnoncredsProofProof(BaseModel):
    """Anoncreds proof.proof content."""

    class Meta:
        """Anoncreds proof.proof content metadata."""

        schema_class = "AnoncredsProofProofSchema"

    def __init__(
        self,
        proofs: Sequence[AnoncredsProofProofProofsProof] = None,
        aggregated_proof: Optional[AnoncredsProofProofAggregatedProof] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof.proof content."""
        super().__init__(**kwargs)
        self.proofs = proofs
        self.aggregated_proof = aggregated_proof


class AnoncredsProofProofSchema(BaseModelSchema):
    """Anoncreds proof.proof content schema."""

    class Meta:
        """Anoncreds proof.proof content schema metadata."""

        model_class = AnoncredsProofProof
        unknown = EXCLUDE

    proofs = fields.Nested(
        AnoncredsProofProofProofsProofSchema,
        many=True,
        metadata={"description": "Anoncreds proof proofs"},
    )
    aggregated_proof = fields.Nested(
        AnoncredsProofProofAggregatedProofSchema,
        metadata={"description": "Anoncreds proof aggregated proof"},
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


class AnoncredsProofRequestedProofRevealedAttr(RawEncoded):
    """Anoncreds proof requested proof revealed attr."""

    class Meta:
        """Anoncreds proof requested proof revealed attr metadata."""

        schema_class = "AnoncredsProofRequestedProofRevealedAttrSchema"

    def __init__(
        self,
        sub_proof_index: Optional[int] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof requested proof revealed attr."""
        super().__init__(**kwargs)
        self.sub_proof_index = sub_proof_index


class AnoncredsProofRequestedProofRevealedAttrSchema(RawEncodedSchema):
    """Anoncreds proof requested proof revealed attr schema."""

    class Meta:
        """Anoncreds proof requested proof revealed attr schema metadata."""

        model_class = AnoncredsProofRequestedProofRevealedAttr
        unknown = EXCLUDE

    sub_proof_index = fields.Int(
        metadata={"strict": True, "description": "Sub-proof index"}
    )


class AnoncredsProofRequestedProofRevealedAttrGroup(BaseModel):
    """Anoncreds proof requested proof revealed attr group."""

    class Meta:
        """Anoncreds proof requested proof revealed attr group metadata."""

        schema_class = "AnoncredsProofRequestedProofRevealedAttrGroupSchema"

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


class AnoncredsProofRequestedProofRevealedAttrGroupSchema(BaseModelSchema):
    """Anoncreds proof requested proof revealed attr group schema."""

    class Meta:
        """Anoncreds proof requested proof revealed attr group schema metadata."""

        model_class = AnoncredsProofRequestedProofRevealedAttrGroup
        unknown = EXCLUDE

    sub_proof_index = fields.Int(
        metadata={"strict": True, "description": "Sub-proof index"}
    )
    values = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(RawEncodedSchema),
        metadata={
            "description": "Anoncreds proof requested proof revealed attr groups group value"  # noqa: E501
        },
    )


class AnoncredsProofRequestedProofPredicate(BaseModel):
    """Anoncreds proof requested proof predicate."""

    class Meta:
        """Anoncreds proof requested proof requested proof predicate metadata."""

        schema_class = "AnoncredsProofRequestedProofPredicateSchema"

    def __init__(
        self,
        sub_proof_index: Optional[int] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof requested proof predicate."""
        super().__init__(**kwargs)
        self.sub_proof_index = sub_proof_index


class AnoncredsProofRequestedProofPredicateSchema(BaseModelSchema):
    """Anoncreds proof requested prrof predicate schema."""

    class Meta:
        """Anoncreds proof requested proof requested proof predicate schema metadata."""

        model_class = AnoncredsProofRequestedProofPredicate
        unknown = EXCLUDE

    sub_proof_index = fields.Int(
        metadata={"strict": True, "description": "Sub-proof index"}
    )


class AnoncredsProofRequestedProof(BaseModel):
    """Anoncreds proof.requested_proof content."""

    class Meta:
        """Anoncreds proof.requested_proof content metadata."""

        schema_class = "AnoncredsProofRequestedProofSchema"

    def __init__(
        self,
        revealed_attrs: Mapping[str, AnoncredsProofRequestedProofRevealedAttr] = None,
        revealed_attr_groups: Mapping[
            str,
            AnoncredsProofRequestedProofRevealedAttrGroup,
        ] = None,
        self_attested_attrs: Optional[Mapping] = None,
        unrevealed_attrs: Optional[Mapping] = None,
        predicates: Mapping[str, AnoncredsProofRequestedProofPredicate] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof requested proof."""
        super().__init__(**kwargs)
        self.revealed_attrs = revealed_attrs
        self.revealed_attr_groups = revealed_attr_groups
        self.self_attested_attrs = self_attested_attrs
        self.unrevealed_attrs = unrevealed_attrs
        self.predicates = predicates


class AnoncredsProofRequestedProofSchema(BaseModelSchema):
    """Anoncreds proof requested proof schema."""

    class Meta:
        """Anoncreds proof requested proof schema metadata."""

        model_class = AnoncredsProofRequestedProof
        unknown = EXCLUDE

    revealed_attrs = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(AnoncredsProofRequestedProofRevealedAttrSchema),
        allow_none=True,
        metadata={"description": "Proof requested proof revealed attributes"},
    )
    revealed_attr_groups = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(AnoncredsProofRequestedProofRevealedAttrGroupSchema),
        allow_none=True,
        metadata={"description": "Proof requested proof revealed attribute groups"},
    )
    self_attested_attrs = fields.Dict(
        metadata={"description": "Proof requested proof self-attested attributes"}
    )
    unrevealed_attrs = fields.Dict(metadata={"description": "Unrevealed attributes"})
    predicates = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(AnoncredsProofRequestedProofPredicateSchema),
        metadata={"description": "Proof requested proof predicates."},
    )


class AnoncredsProofIdentifier(BaseModel):
    """Anoncreds proof identifier."""

    class Meta:
        """Anoncreds proof identifier metadata."""

        schema_class = "AnoncredsProofIdentifierSchema"

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


class AnoncredsProofIdentifierSchema(BaseModelSchema):
    """Anoncreds proof identifier schema."""

    class Meta:
        """Anoncreds proof identifier schema metadata."""

        model_class = AnoncredsProofIdentifier
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


class AnoncredsProof(BaseModel):
    """Anoncreds proof."""

    class Meta:
        """Anoncreds proof metadata."""

        schema_class = "AnoncredsProofSchema"

    def __init__(
        self,
        proof: Optional[AnoncredsProofProof] = None,
        requested_proof: Optional[AnoncredsProofRequestedProof] = None,
        identifiers: Sequence[AnoncredsProofIdentifier] = None,
        **kwargs,
    ):
        """Initialize anoncreds proof."""
        super().__init__(**kwargs)
        self.proof = proof
        self.requested_proof = requested_proof
        self.identifiers = identifiers


class AnoncredsProofSchema(BaseModelSchema):
    """Anoncreds proof schema."""

    class Meta:
        """Anoncreds proof schema metadata."""

        model_class = AnoncredsProof
        unknown = EXCLUDE

    proof = fields.Nested(
        AnoncredsProofProofSchema,
        metadata={"description": "Anoncreds proof.proof content"},
    )
    requested_proof = fields.Nested(
        AnoncredsProofRequestedProofSchema,
        metadata={"description": "Anoncreds proof.requested_proof content"},
    )
    identifiers = fields.Nested(
        AnoncredsProofIdentifierSchema,
        many=True,
        metadata={"description": "Anoncreds proof.identifiers content"},
    )


class AnoncredsPresSpecSchema(AdminAPIMessageTracingSchema):
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
        values=fields.Nested(AnoncredsRequestedCredsRequestedAttrSchema),
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
        values=fields.Nested(AnoncredsRequestedCredsRequestedPredSchema),
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
