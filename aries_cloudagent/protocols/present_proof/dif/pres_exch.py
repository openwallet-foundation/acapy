"""Schemas for dif presentation exchange attachment."""
from marshmallow import (
    fields,
    validate,
    EXCLUDE,
    INCLUDE,
    pre_load,
    post_dump,
    ValidationError,
)
from typing import Sequence, Union, Mapping

from ....messaging.models.base import BaseModelSchema, BaseModel
from ....messaging.valid import (
    UUID4,
    StrOrDictField,
    StrOrNumberField,
)
from ....vc.vc_ld import LinkedDataProofSchema


class ClaimFormat(BaseModel):
    """Defines Claim field."""

    class Meta:
        """ClaimFormat metadata."""

        schema_class = "ClaimFormatSchema"

    def __init__(
        self,
        *,
        jwt: Mapping = None,
        jwt_vc: Mapping = None,
        jwt_vp: Mapping = None,
        ldp: Mapping = None,
        ldp_vc: Mapping = None,
        ldp_vp: Mapping = None,
    ):
        """Initialize format."""
        self.jwt = jwt
        self.jwt_vc = jwt_vc
        self.jwt_vp = jwt_vp
        self.ldp = ldp
        self.ldp_vc = ldp_vc
        self.ldp_vp = ldp_vp


class ClaimFormatSchema(BaseModelSchema):
    """Single ClaimFormat Schema."""

    class Meta:
        """ClaimFormatSchema metadata."""

        model_class = ClaimFormat
        unknown = EXCLUDE

    jwt = fields.Dict(
        required=False,
    )
    jwt_vc = fields.Dict(
        required=False,
    )
    jwt_vp = fields.Dict(
        required=False,
    )
    ldp = fields.Dict(
        required=False,
    )
    ldp_vc = fields.Dict(
        required=False,
    )
    ldp_vp = fields.Dict(
        required=False,
    )


class SubmissionRequirements(BaseModel):
    """describes input to be submitted via a presentation submission."""

    class Meta:
        """SubmissionRequirements metadata."""

        schema_class = "SubmissionRequirementsSchema"

    def __init__(
        self,
        *,
        _name: str = None,
        purpose: str = None,
        rule: str = None,
        count: int = None,
        minimum: int = None,
        maximum: int = None,
        _from: str = None,
        # Self_reference
        from_nested: Sequence = None,
    ):
        """Initialize SubmissionRequirement."""
        self._name = _name
        self.purpose = purpose
        self.rule = rule
        self.count = count
        self.minimum = minimum
        self.maximum = maximum
        self._from = _from
        self.from_nested = from_nested


class SubmissionRequirementsSchema(BaseModelSchema):
    """Single Presentation Definition Schema."""

    class Meta:
        """SubmissionRequirementsSchema metadata."""

        model_class = SubmissionRequirements
        unknown = EXCLUDE

    _name = fields.Str(description="Name", required=False, data_key="name")
    purpose = fields.Str(description="Purpose", required=False)
    rule = fields.Str(
        description="Selection",
        required=False,
        validate=validate.OneOf(["all", "pick"]),
    )
    count = fields.Int(
        description="Count Value",
        example=1234,
        required=False,
        strict=True,
    )
    minimum = fields.Int(
        description="Min Value",
        example=1234,
        required=False,
        strict=True,
        data_key="min",
    )
    maximum = fields.Int(
        description="Max Value",
        example=1234,
        required=False,
        strict=True,
        data_key="max",
    )
    _from = fields.Str(description="From", required=False, data_key="from")
    # Self References
    from_nested = fields.List(
        fields.Nested(lambda: SubmissionRequirementsSchema()),
        required=False,
    )

    @pre_load
    def validate_from(self, data, **kwargs):
        """Support validation of from and from_nested."""
        if "from" in data and "from_nested" in data:
            raise ValidationError(
                "Both from and from_nested cannot be "
                "specified in the submission requirement"
            )
        if "from" not in data and "from_nested" not in data:
            raise ValidationError(
                "Either from or from_nested needs to be "
                "specified in the submission requirement"
            )
        return data


class SchemaInputDescriptor(BaseModel):
    """SchemaInputDescriptor."""

    class Meta:
        """SchemaInputDescriptor metadata."""

        schema_class = "SchemaInputDescriptorSchema"

    def __init__(
        self,
        *,
        uri: str = None,
        required: bool = None,
    ):
        """Initialize SchemaInputDescriptor."""
        self.uri = uri
        self.required = required


class SchemaInputDescriptorSchema(BaseModelSchema):
    """Single SchemaField Schema."""

    class Meta:
        """SchemaInputDescriptorSchema metadata."""

        model_class = SchemaInputDescriptor
        unknown = EXCLUDE

    uri = fields.Str(
        description="URI",
        required=False,
    )
    required = fields.Bool(description="Required", required=False)


class SchemasInputDescriptorFilter(BaseModel):
    """SchemasInputDescriptorFilter."""

    class Meta:
        """InputDescriptor Schemas filter metadata."""

        schema_class = "SchemasInputDescriptorFilterSchema"

    def __init__(
        self,
        *,
        oneof_filter: bool = False,
        uri_groups: Sequence[Sequence[SchemaInputDescriptor]] = None,
    ):
        """Initialize SchemasInputDescriptorFilter."""
        self.oneof_filter = oneof_filter
        self.uri_groups = uri_groups


class SchemasInputDescriptorFilterSchema(BaseModelSchema):
    """Single SchemasInputDescriptorFilterSchema Schema."""

    class Meta:
        """SchemasInputDescriptorFilterSchema metadata."""

        model_class = SchemasInputDescriptorFilter
        unknown = EXCLUDE

    uri_groups = fields.List(fields.List(fields.Nested(SchemaInputDescriptorSchema)))
    oneof_filter = fields.Bool(description="oneOf")

    @pre_load
    def extract_info(self, data, **kwargs):
        """deserialize."""
        new_data = {}
        if isinstance(data, dict):
            if "uri_groups" in data:
                return data
            elif "oneof_filter" in data and isinstance(data["oneof_filter"], list):
                new_data["oneof_filter"] = True
                uri_group_list_of_list = []
                uri_group_list = data.get("oneof_filter")
                for uri_group in uri_group_list:
                    if isinstance(uri_group, list):
                        uri_group_list_of_list.append(uri_group)
                    else:
                        uri_group_list_of_list.append([uri_group])
                new_data["uri_groups"] = uri_group_list_of_list
        elif isinstance(data, list):
            new_data["oneof_filter"] = False
            new_data["uri_groups"] = [data]
        data = new_data
        return data


class DIFHolder(BaseModel):
    """Single Holder object for Constraints."""

    class Meta:
        """Holder metadata."""

        schema_class = "DIFHolderSchema"

    def __init__(
        self,
        *,
        field_ids: Sequence[str] = None,
        directive: str = None,
    ):
        """Initialize Holder."""
        self.field_ids = field_ids
        self.directive = directive


class DIFHolderSchema(BaseModelSchema):
    """Single Holder Schema."""

    class Meta:
        """DIFHolderSchema metadata."""

        model_class = DIFHolder
        unknown = EXCLUDE

    field_ids = fields.List(
        fields.Str(
            description="FieldID",
            required=False,
            **UUID4,
        ),
        required=False,
        data_key="field_id",
    )
    directive = fields.Str(
        description="Preference",
        required=False,
        validate=validate.OneOf(["required", "preferred"]),
    )


class Filter(BaseModel):
    """Single Filter for the Constraint object."""

    class Meta:
        """Filter metadata."""

        schema_class = "FilterSchema"

    def __init__(
        self,
        *,
        _not: bool = False,
        _type: str = None,
        fmt: str = None,
        pattern: str = None,
        minimum: str = None,
        maximum: str = None,
        min_length: int = None,
        max_length: int = None,
        exclusive_min: str = None,
        exclusive_max: str = None,
        const: str = None,
        enums: Sequence[str] = None,
    ):
        """Initialize Filter."""
        self._type = _type
        self.fmt = fmt
        self.pattern = pattern
        self.minimum = minimum
        self.maximum = maximum
        self.min_length = min_length
        self.max_length = max_length
        self.exclusive_min = exclusive_min
        self.exclusive_max = exclusive_max
        self.const = const
        self.enums = enums
        self._not = _not


class FilterSchema(BaseModelSchema):
    """Single Filter Schema."""

    class Meta:
        """FilterSchema metadata."""

        model_class = Filter
        unknown = EXCLUDE

    _type = fields.Str(description="Type", required=False, data_key="type")
    fmt = fields.Str(
        description="Format",
        required=False,
        data_key="format",
    )
    pattern = fields.Str(
        description="Pattern",
        required=False,
    )
    minimum = StrOrNumberField(
        description="Minimum",
        required=False,
    )
    maximum = StrOrNumberField(
        description="Maximum",
        required=False,
    )
    min_length = fields.Int(
        description="Min Length",
        example=1234,
        strict=True,
        required=False,
        data_key="minLength",
    )
    max_length = fields.Int(
        description="Max Length",
        example=1234,
        strict=True,
        required=False,
        data_key="maxLength",
    )
    exclusive_min = StrOrNumberField(
        description="ExclusiveMinimum",
        required=False,
        data_key="exclusiveMinimum",
    )
    exclusive_max = StrOrNumberField(
        description="ExclusiveMaximum",
        required=False,
        data_key="exclusiveMaximum",
    )
    const = StrOrNumberField(
        description="Const",
        required=False,
    )
    enums = fields.List(
        StrOrNumberField(description="Enum", required=False),
        required=False,
        data_key="enum",
    )
    _not = fields.Boolean(
        description="Not",
        required=False,
        example=False,
        data_key="not",
    )

    @pre_load
    def extract_info(self, data, **kwargs):
        """Enum validation and not filter logic."""
        if "not" in data:
            new_data = {"not": True}
            for key, value in data.get("not").items():
                new_data[key] = value
            data = new_data
        if "enum" in data:
            if type(data.get("enum")) is not list:
                raise ValidationError("enum is not specified as a list")
        return data

    @post_dump
    def serialize_reformat(self, data, **kwargs):
        """Support serialization of not filter according to DIF spec."""
        if data.pop("not", False):
            return {"not": data}

        return data


class DIFField(BaseModel):
    """Single Field object for the Constraint."""

    class Meta:
        """Field metadata."""

        schema_class = "DIFFieldSchema"

    def __init__(
        self,
        *,
        id: str = None,
        paths: Sequence[str] = None,
        purpose: str = None,
        predicate: str = None,
        _filter: Filter = None,
    ):
        """Initialize Field."""
        self.paths = paths
        self.purpose = purpose
        self.predicate = predicate
        self._filter = _filter
        self.id = id


class DIFFieldSchema(BaseModelSchema):
    """Single Field Schema."""

    class Meta:
        """DIFFieldSchema metadata."""

        model_class = DIFField
        unknown = EXCLUDE

    id = fields.Str(description="ID", required=False)
    paths = fields.List(
        fields.Str(description="Path", required=False),
        required=False,
        data_key="path",
    )
    purpose = fields.Str(
        description="Purpose",
        required=False,
    )
    predicate = fields.Str(
        description="Preference",
        required=False,
        validate=validate.OneOf(["required", "preferred"]),
    )
    _filter = fields.Nested(FilterSchema, data_key="filter")


class Constraints(BaseModel):
    """Single Constraints which describes InputDescriptor's Contraint field."""

    class Meta:
        """Constraints metadata."""

        schema_class = "ConstraintsSchema"

    def __init__(
        self,
        *,
        subject_issuer: str = None,
        limit_disclosure: bool = None,
        holders: Sequence[DIFHolder] = None,
        _fields: Sequence[DIFField] = None,
        status_active: str = None,
        status_suspended: str = None,
        status_revoked: str = None,
    ):
        """Initialize Constraints for Input Descriptor."""
        self.subject_issuer = subject_issuer
        self.limit_disclosure = limit_disclosure
        self.holders = holders
        self._fields = _fields
        self.status_active = status_active
        self.status_suspended = status_suspended
        self.status_revoked = status_revoked


class ConstraintsSchema(BaseModelSchema):
    """Single Constraints Schema."""

    class Meta:
        """ConstraintsSchema metadata."""

        model_class = Constraints
        unknown = EXCLUDE

    subject_issuer = fields.Str(
        description="SubjectIsIssuer",
        required=False,
        validate=validate.OneOf(["required", "preferred"]),
        data_key="subject_is_issuer",
    )
    limit_disclosure = fields.Str(description="LimitDisclosure", required=False)
    holders = fields.List(
        fields.Nested(DIFHolderSchema),
        required=False,
        data_key="is_holder",
    )
    _fields = fields.List(
        fields.Nested(DIFFieldSchema),
        required=False,
        data_key="fields",
    )
    status_active = fields.Str(
        required=False,
        validate=validate.OneOf(["required", "allowed", "disallowed"]),
    )
    status_suspended = fields.Str(
        required=False,
        validate=validate.OneOf(["required", "allowed", "disallowed"]),
    )
    status_revoked = fields.Str(
        required=False,
        validate=validate.OneOf(["required", "allowed", "disallowed"]),
    )

    @pre_load
    def extract_info(self, data, **kwargs):
        """Support deserialization of statuses according to DIF spec."""
        if "statuses" in data:
            if "active" in data.get("statuses"):
                if "directive" in data.get("statuses").get("active"):
                    data["status_active"] = data["statuses"]["active"]["directive"]
            if "suspended" in data.get("statuses"):
                if "directive" in data.get("statuses").get("suspended"):
                    data["status_suspended"] = data["statuses"]["suspended"][
                        "directive"
                    ]
            if "revoked" in data.get("statuses"):
                if "directive" in data.get("statuses").get("revoked"):
                    data["status_revoked"] = data["statuses"]["revoked"]["directive"]
        return data

    @post_dump
    def reformat_data(self, data, **kwargs):
        """Support serialization of statuses according to DIF spec."""
        if "status_active" in data:
            statuses = data.get("statuses", {})
            statuses["active"] = {"directive": data.get("status_active")}
            data["statuses"] = statuses
            del data["status_active"]
        if "status_suspended" in data:
            statuses = data.get("statuses", {})
            statuses["suspended"] = {"directive": data.get("status_suspended")}
            data["statuses"] = statuses
            del data["status_suspended"]
        if "status_revoked" in data:
            statuses = data.get("statuses", {})
            statuses["revoked"] = {"directive": data.get("status_revoked")}
            data["statuses"] = statuses
            del data["status_revoked"]
        return data


class InputDescriptors(BaseModel):
    """Input Descriptors."""

    class Meta:
        """InputDescriptors metadata."""

        schema_class = "InputDescriptorsSchema"

    def __init__(
        self,
        *,
        id: str = None,
        groups: Sequence[str] = None,
        name: str = None,
        purpose: str = None,
        metadata: dict = None,
        constraint: Constraints = None,
        schemas: SchemasInputDescriptorFilter = None,
    ):
        """Initialize InputDescriptors."""
        self.id = id
        self.groups = groups
        self.name = name
        self.purpose = purpose
        self.metadata = metadata
        self.constraint = constraint
        self.schemas = schemas


class InputDescriptorsSchema(BaseModelSchema):
    """Single InputDescriptors Schema."""

    class Meta:
        """InputDescriptorsSchema metadata."""

        model_class = InputDescriptors
        unknown = EXCLUDE

    id = fields.Str(description="ID", required=False)
    groups = fields.List(
        fields.Str(
            description="Group",
            required=False,
        ),
        required=False,
        data_key="group",
    )
    name = fields.Str(description="Name", required=False)
    purpose = fields.Str(description="Purpose", required=False)
    metadata = fields.Dict(description="Metadata dictionary", required=False)
    constraint = fields.Nested(
        ConstraintsSchema, required=False, data_key="constraints"
    )
    schemas = fields.Nested(
        SchemasInputDescriptorFilterSchema,
        required=False,
        data_key="schema",
        description=(
            "Accepts a list of schema or a dict containing filters like oneof_filter."
        ),
        example=(
            {
                "oneof_filter": [
                    [
                        {"uri": "https://www.w3.org/Test1#Test1"},
                        {"uri": "https://www.w3.org/Test2#Test2"},
                    ],
                    {
                        "oneof_filter": [
                            [{"uri": "https://www.w3.org/Test1#Test1"}],
                            [{"uri": "https://www.w3.org/Test2#Test2"}],
                        ]
                    },
                ]
            }
        ),
    )


class Requirement(BaseModel):
    """Single Requirement generated from toRequirement function."""

    class Meta:
        """Requirement metadata."""

        schema_class = "RequirementSchema"

    def __init__(
        self,
        *,
        count: int = None,
        maximum: int = None,
        minimum: int = None,
        input_descriptors: Sequence[InputDescriptors] = None,
        nested_req: Sequence = None,
    ):
        """Initialize Requirement."""
        self.count = count
        self.maximum = maximum
        self.minimum = minimum
        self.input_descriptors = input_descriptors
        self.nested_req = nested_req


class RequirementSchema(BaseModelSchema):
    """Single Requirement Schema."""

    class Meta:
        """RequirementSchema metadata."""

        model_class = Requirement
        unknown = EXCLUDE

    count = fields.Int(
        description="Count Value",
        example=1234,
        strict=True,
        required=False,
    )
    maximum = fields.Int(
        description="Max Value",
        example=1234,
        strict=True,
        required=False,
    )
    minimum = fields.Int(
        description="Min Value",
        example=1234,
        strict=True,
        required=False,
    )
    input_descriptors = fields.List(
        fields.Nested(InputDescriptorsSchema),
        required=False,
    )
    # Self References
    nested_req = fields.List(
        fields.Nested(lambda: RequirementSchema(exclude=("_nested_req",))),
        required=False,
    )


class PresentationDefinition(BaseModel):
    """https://identity.foundation/presentation-exchange/."""

    class Meta:
        """PresentationDefinition metadata."""

        schema_class = "PresentationDefinitionSchema"

    def __init__(
        self,
        *,
        id: str = None,
        name: str = None,
        purpose: str = None,
        fmt: ClaimFormat = None,
        submission_requirements: Sequence[SubmissionRequirements] = None,
        input_descriptors: Sequence[InputDescriptors] = None,
        **kwargs,
    ):
        """Initialize flattened single-JWS to include in attach decorator data."""
        super().__init__(**kwargs)
        self.id = id
        self.name = name
        self.purpose = purpose
        self.fmt = fmt
        self.submission_requirements = submission_requirements
        self.input_descriptors = input_descriptors


class PresentationDefinitionSchema(BaseModelSchema):
    """Single Presentation Definition Schema."""

    class Meta:
        """PresentationDefinitionSchema metadata."""

        model_class = PresentationDefinition
        unknown = EXCLUDE

    id = fields.Str(
        required=False,
        description="Unique Resource Identifier",
        **UUID4,
    )
    name = fields.Str(
        description=(
            "Human-friendly name that describes"
            " what the presentation definition pertains to"
        ),
        required=False,
    )
    purpose = fields.Str(
        description=(
            "Describes the purpose for which"
            " the Presentation Definition's inputs are being requested"
        ),
        required=False,
    )
    fmt = fields.Nested(
        ClaimFormatSchema,
        required=False,
        data_key="format",
    )
    submission_requirements = fields.List(
        fields.Nested(SubmissionRequirementsSchema),
        required=False,
    )
    input_descriptors = fields.List(
        fields.Nested(InputDescriptorsSchema),
        required=False,
    )


class InputDescriptorMapping(BaseModel):
    """Single InputDescriptorMapping object."""

    class Meta:
        """InputDescriptorMapping metadata."""

        schema_class = "InputDescriptorMappingSchema"

    def __init__(
        self,
        *,
        id: str = None,
        fmt: str = None,
        path: str = None,
    ):
        """Initialize InputDescriptorMapping."""
        self.id = id
        self.fmt = fmt
        self.path = path


class InputDescriptorMappingSchema(BaseModelSchema):
    """Single InputDescriptorMapping Schema."""

    class Meta:
        """InputDescriptorMappingSchema metadata."""

        model_class = InputDescriptorMapping
        unknown = EXCLUDE

    id = fields.Str(
        description="ID",
        required=False,
    )
    fmt = fields.Str(
        description="Format",
        required=False,
        default="ldp_vc",
        data_key="format",
    )
    path = fields.Str(
        description="Path",
        required=False,
    )


class PresentationSubmission(BaseModel):
    """Single PresentationSubmission object."""

    class Meta:
        """PresentationSubmission metadata."""

        schema_class = "PresentationSubmissionSchema"

    def __init__(
        self,
        *,
        id: str = None,
        definition_id: str = None,
        descriptor_maps: Sequence[InputDescriptorMapping] = None,
    ):
        """Initialize InputDescriptorMapping."""
        self.id = id
        self.definition_id = definition_id
        self.descriptor_maps = descriptor_maps


class PresentationSubmissionSchema(BaseModelSchema):
    """Single PresentationSubmission Schema."""

    class Meta:
        """PresentationSubmissionSchema metadata."""

        model_class = PresentationSubmission
        unknown = EXCLUDE

    id = fields.Str(
        description="ID",
        required=False,
        **UUID4,
    )
    definition_id = fields.Str(
        description="DefinitionID",
        required=False,
        **UUID4,
    )
    descriptor_maps = fields.List(
        fields.Nested(InputDescriptorMappingSchema),
        required=False,
        data_key="descriptor_map",
    )


class VerifiablePresentation(BaseModel):
    """Single VerifiablePresentation object."""

    class Meta:
        """VerifiablePresentation metadata."""

        schema_class = "VerifiablePresentationSchema"

    def __init__(
        self,
        *,
        id: str = None,
        contexts: Sequence[Union[str, dict]] = None,
        types: Sequence[str] = None,
        credentials: Sequence[dict] = None,
        proof: Sequence[dict] = None,
        presentation_submission: PresentationSubmission = None,
    ):
        """Initialize VerifiablePresentation."""
        self.id = id
        self.contexts = contexts
        self.types = types
        self.credentials = credentials
        self.proof = proof
        self.presentation_submission = presentation_submission


class VerifiablePresentationSchema(BaseModelSchema):
    """Single Verifiable Presentation Schema."""

    class Meta:
        """VerifiablePresentationSchema metadata."""

        model_class = VerifiablePresentation
        unknown = INCLUDE

    id = fields.Str(
        description="ID",
        required=False,
        **UUID4,
    )
    contexts = fields.List(
        StrOrDictField(),
        data_key="@context",
    )
    types = fields.List(
        fields.Str(description="Types", required=False),
        data_key="type",
    )
    credentials = fields.List(
        fields.Dict(description="Credentials", required=False),
        data_key="verifiableCredential",
    )
    proof = fields.Nested(
        LinkedDataProofSchema(),
        required=True,
        description="The proof of the credential",
    )
    presentation_submission = fields.Nested(PresentationSubmissionSchema)


class DIFOptions(BaseModel):
    """Single DIFOptions object."""

    class Meta:
        """DIFOptions metadata."""

        schema_class = "DIFOptionsSchema"

    def __init__(
        self,
        *,
        challenge: str = None,
        domain: str = None,
    ):
        """Initialize DIFOptions."""
        self.challenge = challenge
        self.domain = domain


class DIFOptionsSchema(BaseModelSchema):
    """Schema for options required for the Prover to fulfill the Verifier's request."""

    class Meta:
        """DIFOptionsSchema metadata."""

        model_class = DIFOptions
        unknown = EXCLUDE

    challenge = fields.String(
        description="Challenge protect against replay attack",
        required=False,
        **UUID4,
    )
    domain = fields.String(
        description="Domain protect against replay attack",
        required=False,
        example="4jt78h47fh47",
    )
