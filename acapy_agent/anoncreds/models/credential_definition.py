"""AnonCreds cred def OpenAPI validators."""

from typing import Optional

from anoncreds import CredentialDefinition
from marshmallow import EXCLUDE, fields
from marshmallow.validate import OneOf
from typing_extensions import Literal

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    ANONCREDS_DID_EXAMPLE,
    ANONCREDS_SCHEMA_ID_EXAMPLE,
    NUM_STR_WHOLE_EXAMPLE,
    NUM_STR_WHOLE_VALIDATE,
)

NUM_STR_WHOLE = {
    "validate": NUM_STR_WHOLE_VALIDATE,
    "metadata": {"example": NUM_STR_WHOLE_EXAMPLE},
}


class CredDefValuePrimary(BaseModel):
    """PrimarySchema."""

    class Meta:
        """PrimarySchema metadata."""

        schema_class = "CredDefValuePrimarySchemaAnonCreds"

    def __init__(self, n: str, s: str, r: dict, rctxt: str, z: str, **kwargs):
        """Initialize an instance.

        Args:
            n: is a safe RSA-2048 number.
            s: is a randomly selected quadratic residue of n.
            r: is an object that defines a CL-RSA public key fragment
                for each attribute in the credential.
            rctxt: is equal to s^(xrctxt), where xrctxt is a randomly selected integer
                between 2 and p'q'-1.
            z: is equal to s^(xz), where xz is a randomly selected integer between 2
                and p'q'-1. This makes up part of the CL-RSA public key, independent of
                the message blocks being signed.
            kwargs: Keyword arguments
        """
        super().__init__(**kwargs)
        self.n = n
        self.s = s
        self.r = r
        self.rctxt = rctxt
        self.z = z


class CredDefValuePrimarySchemaAnonCreds(BaseModelSchema):
    """Cred def value primary schema."""

    class Meta:
        """CredDefValuePrimarySchema metadata."""

        model_class = CredDefValuePrimary
        unknown = EXCLUDE

    n = fields.Str(**NUM_STR_WHOLE)
    s = fields.Str(**NUM_STR_WHOLE)
    r = fields.Dict()
    rctxt = fields.Str(**NUM_STR_WHOLE)
    z = fields.Str(**NUM_STR_WHOLE)


class CredDefValueRevocation(BaseModel):
    """Cred def value revocation."""

    class Meta:
        """CredDefValueRevocation metadata."""

        schema_class = "CredDefValueRevocationSchemaAnonCreds"

    def __init__(
        self,
        g: str,
        g_dash: str,
        h: str,
        h0: str,
        h1: str,
        h2: str,
        htilde: str,
        h_cap: str,
        u: str,
        pk: str,
        y: str,
    ):
        """Initialize an instance.

        Args:
            g: is a generator for the elliptic curve group G1.
            g_dash: is a generator for the elliptic curve group G2.
            h: is an elliptic curve point selected uniformly at random from G1.
            h0: is an elliptic curve point selected uniformly at random from G1.
            h1: is an elliptic curve point selected uniformly at random from G1.
            h2: is an elliptic curve point selected uniformly at random from G1.
            htilde: is an elliptic curve point selected uniformly at random from G1.
            h_cap: is an elliptic curve point selected uniformly at random from G2.
            u: is an elliptic curve point selected uniformly at random from G2.
            pk: is the public key in G1 for the issuer with respect to this accumulator,
                computed as g^sk (in multiplicative notation), where sk is from
                r_key above.
            y: is the an elliptic curve point in G2. computed as h_cap^x
                (in multiplicative notation), where x is from r_key above
        """
        self.g = g
        self.g_dash = g_dash
        self.h = h
        self.h0 = h0
        self.h1 = h1
        self.h2 = h2
        self.htilde = htilde
        self.h_cap = h_cap
        self.u = u
        self.pk = pk
        self.y = y


class CredDefValueRevocationSchemaAnonCreds(BaseModelSchema):
    """Cred def value revocation schema."""

    class Meta:
        """Metadata."""

        model_class = CredDefValueRevocation
        unknown = EXCLUDE

    g = fields.Str(metadata={"example": "1 1F14F&ECB578F 2 095E45DDF417D"})
    g_dash = fields.Str(
        metadata={"example": "1 1D64716fCDC00C 1 0C781960FA66E3D3 2 095E45DDF417D"}
    )
    h = fields.Str(metadata={"example": "1 16675DAE54BFAE8 2 095E45DD417D"})
    h0 = fields.Str(metadata={"example": "1 21E5EF9476EAF18 2 095E45DDF417D"})
    h1 = fields.Str(metadata={"example": "1 236D1D99236090 2 095E45DDF417D"})
    h2 = fields.Str(metadata={"example": "1 1C3AE8D1F1E277 2 095E45DDF417D"})
    htilde = fields.Str(metadata={"example": "1 1D8549E8C0F8 2 095E45DDF417D"})
    h_cap = fields.Str(
        metadata={"example": "1 1B2A32CF3167 1 2490FEBF6EE55 1 0000000000000000"}
    )
    u = fields.Str(
        metadata={"example": "1 0C430AAB2B4710 1 1CB3A0932EE7E 1 0000000000000000"}
    )
    pk = fields.Str(
        metadata={"example": "1 142CD5E5A7DC 1 153885BD903312 2 095E45DDF417D"}
    )
    y = fields.Str(
        metadata={"example": "1 153558BD903312 2 095E45DDF417D 1 0000000000000000"}
    )


class CredDefValue(BaseModel):
    """Cred def value."""

    class Meta:
        """CredDefValue metadata."""

        schema_class = "CredDefValueSchemaAnonCreds"

    def __init__(
        self,
        primary: CredDefValuePrimary,
        revocation: Optional[CredDefValueRevocation] = None,
        **kwargs,
    ):
        """Initialize an instance.

        Args:
            primary: Cred Def value primary
            revocation: Cred Def value revocation
            kwargs: Keyword arguments
        """
        super().__init__(**kwargs)
        self.primary = primary
        self.revocation = revocation


class CredDefValueSchemaAnonCreds(BaseModelSchema):
    """Cred def value schema."""

    class Meta:
        """CredDefValueSchema metadata."""

        model_class = CredDefValue
        unknown = EXCLUDE

    primary = fields.Nested(
        CredDefValuePrimarySchemaAnonCreds(),
        metadata={"description": "Primary value for credential definition"},
    )
    revocation = fields.Nested(
        CredDefValueRevocationSchemaAnonCreds(),
        metadata={"description": "Revocation value for credential definition"},
        required=False,
    )


class CredDef(BaseModel):
    """AnonCredsCredDef."""

    class Meta:
        """AnonCredsCredDef metadata."""

        schema_class = "CredDefSchema"

    def __init__(
        self,
        issuer_id: str,
        schema_id: str,
        type: Literal["CL"],
        tag: str,
        value: CredDefValue,
        **kwargs,
    ):
        """Initialize an instance.

        Args:
            issuer_id: Issuer ID
            schema_id: Schema ID
            type: Type
            tag: Tag
            value: Cred Def value
            kwargs: Keyword arguments
        """
        super().__init__(**kwargs)
        self.issuer_id = issuer_id
        self.schema_id = schema_id
        self.type = type
        self.tag = tag
        self.value = value

    @classmethod
    def from_native(cls, cred_def: CredentialDefinition):
        """Convert a native credential definition to a CredDef object."""
        return cls.deserialize(cred_def.to_json())

    def to_native(self) -> CredentialDefinition:
        """Convert to native anoncreds credential definition."""
        return CredentialDefinition.load(self.serialize())


class CredDefSchema(BaseModelSchema):
    """CredDefSchema."""

    class Meta:
        """CredDefSchema metadata."""

        model_class = CredDef
        unknown = EXCLUDE

    issuer_id = fields.Str(
        metadata={
            "description": "Issuer Identifier of the credential definition or schema",
            "example": ANONCREDS_DID_EXAMPLE,
        },
        data_key="issuerId",
    )
    schema_id = fields.Str(
        data_key="schemaId",
        metadata={
            "description": "Schema identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        },
    )
    type = fields.Str(validate=OneOf(["CL"]))
    tag = fields.Str(
        metadata={
            "description": (
                "The tag value passed in by the Issuer to "
                "an AnonCred's Credential Definition create and store implementation."
            ),
            "example": "default",
        }
    )
    value = fields.Nested(CredDefValueSchemaAnonCreds())


class CredDefState(BaseModel):
    """CredDefState."""

    STATE_FINISHED = "finished"
    STATE_FAILED = "failed"
    STATE_ACTION = "action"
    STATE_WAIT = "wait"

    class Meta:
        """CredDefState metadata."""

        schema_class = "CredDefStateSchema"

    def __init__(
        self,
        state: str,
        credential_definition_id: Optional[str],
        credential_definition: CredDef,
    ):
        """Initialize an instance.

        Args:
            state: State
            credential_definition_id: Cred Def ID
            credential_definition: Cred Def
        """
        self.state = state
        self.credential_definition_id = credential_definition_id
        self.credential_definition = credential_definition


class CredDefStateSchema(BaseModelSchema):
    """CredDefStateSchema."""

    class Meta:
        """CredDefStateSchema metadata."""

        model_class = CredDefState
        unknown = EXCLUDE

    state = fields.Str(
        validate=OneOf(
            [
                CredDefState.STATE_FINISHED,
                CredDefState.STATE_FAILED,
                CredDefState.STATE_ACTION,
                CredDefState.STATE_WAIT,
            ]
        )
    )
    credential_definition_id = fields.Str(
        metadata={
            "description": "credential definition id",
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
        },
        allow_none=True,
    )
    credential_definition = fields.Nested(
        CredDefSchema(), metadata={"description": "credential definition"}
    )


class CredDefResult(BaseModel):
    """Cred def result."""

    class Meta:
        """CredDefResult metadata."""

        schema_class = "CredDefResultSchema"

    def __init__(
        self,
        job_id: Optional[str],
        credential_definition_state: CredDefState,
        registration_metadata: dict,
        credential_definition_metadata: dict,
        **kwargs,
    ):
        """Initialize an instance.

        Args:
            job_id: Job ID
            credential_definition_state: Cred Def state
            registration_metadata: Registration metadata
            credential_definition_metadata: Cred Def metadata
            kwargs: Keyword arguments
        """
        super().__init__(**kwargs)
        self.job_id = job_id
        self.credential_definition_state = credential_definition_state
        self.registration_metadata = registration_metadata
        self.credential_definition_metadata = credential_definition_metadata


class CredDefResultSchema(BaseModelSchema):
    """Cred def result schema."""

    class Meta:
        """CredDefResultSchema metadata."""

        model_class = CredDefResult
        unknown = EXCLUDE

    job_id = fields.Str()
    credential_definition_state = fields.Nested(CredDefStateSchema())
    registration_metadata = fields.Dict()
    # For indy, credential_definition_metadata will contain the seqNo
    credential_definition_metadata = fields.Dict()


class GetCredDefResult(BaseModel):
    """Get cred def result."""

    class Meta:
        """AnonCredsRegistryGetCredDef metadata."""

        schema_class = "GetCredDefResultSchema"

    def __init__(
        self,
        credential_definition_id: str,
        credential_definition: CredDef,
        resolution_metadata: dict,
        credential_definition_metadata: dict,
        **kwargs,
    ):
        """Initialize an instance.

        Args:
            credential_definition_id: Cred Def ID
            credential_definition: Cred Def
            resolution_metadata: Resolution metadata
            credential_definition_metadata: Cred Def metadata
            kwargs: Keyword arguments
        """
        super().__init__(**kwargs)
        self.credential_definition_id = credential_definition_id
        self.credential_definition = credential_definition
        self.resolution_metadata = resolution_metadata
        self.credential_definition_metadata = credential_definition_metadata


class GetCredDefResultSchema(BaseModelSchema):
    """GetCredDefResultSchema."""

    class Meta:
        """GetCredDefResultSchema metadata."""

        model_class = GetCredDefResult
        unknown = EXCLUDE

    credential_definition_id = fields.Str(
        metadata={
            "description": "credential definition id",
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
        },
    )
    credential_definition = fields.Nested(
        CredDefSchema(), metadata={"description": "credential definition"}
    )
    resolution_metadata = fields.Dict()
    credential_definitions_metadata = fields.Dict()
