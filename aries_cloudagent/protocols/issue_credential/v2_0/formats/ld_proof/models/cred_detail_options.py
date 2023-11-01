"""LDProofVCDetailOptions."""

from typing import Optional

from marshmallow import INCLUDE, Schema, fields

from .......messaging.models.base import BaseModel, BaseModelSchema
from .......messaging.valid import (
    INDY_ISO8601_DATETIME_EXAMPLE,
    INDY_ISO8601_DATETIME_VALIDATE,
    UUID4_EXAMPLE,
)


class LDProofVCDetailOptions(BaseModel):
    """Linked Data Proof verifiable credential options model."""

    class Meta:
        """LDProofVCDetailOptions metadata."""

        schema_class = "LDProofVCDetailOptionsSchema"

    def __init__(
        self,
        proof_type: Optional[str] = None,
        proof_purpose: Optional[str] = None,
        created: Optional[str] = None,
        domain: Optional[str] = None,
        challenge: Optional[str] = None,
        credential_status: Optional[dict] = None,
    ) -> None:
        """Initialize the LDProofVCDetailOptions instance."""

        self.proof_type = proof_type
        self.proof_purpose = proof_purpose
        self.created = created
        self.domain = domain
        self.challenge = challenge
        self.credential_status = credential_status

    def __eq__(self, o: object) -> bool:
        """Check equalness."""
        if isinstance(o, LDProofVCDetailOptions):
            return (
                self.proof_type == o.proof_type
                and self.proof_purpose == o.proof_purpose
                and self.created == o.created
                and self.domain == o.domain
                and self.challenge == o.challenge
                and self.credential_status == o.credential_status
            )

        return False


class CredentialStatusOptionsSchema(Schema):
    """Linked data proof credential status options schema."""

    class Meta:
        """Accept parameter overload."""

        unknown = INCLUDE

    type = fields.Str(
        required=True,
        metadata={
            "description": (
                "Credential status method type to use for the credential. Should match"
                " status method registered in the Verifiable Credential Extension"
                " Registry"
            ),
            "example": "CredentialStatusList2017",
        },
    )


class LDProofVCDetailOptionsSchema(BaseModelSchema):
    """Linked data proof verifiable credential options schema."""

    class Meta:
        """Accept parameter overload."""

        unknown = INCLUDE
        model_class = LDProofVCDetailOptions

    proof_type = fields.Str(
        data_key="proofType",
        required=True,
        metadata={
            "description": (
                "The proof type used for the proof. Should match suites registered in"
                " the Linked Data Cryptographic Suite Registry"
            ),
            "example": "Ed25519Signature2018",
        },
    )

    proof_purpose = fields.Str(
        data_key="proofPurpose",
        required=False,
        metadata={
            "description": (
                "The proof purpose used for the proof. Should match proof purposes"
                " registered in the Linked Data Proofs Specification"
            ),
            "example": "assertionMethod",
        },
    )

    created = fields.Str(
        required=False,
        validate=INDY_ISO8601_DATETIME_VALIDATE,
        metadata={
            "description": (
                "The date and time of the proof (with a maximum accuracy in seconds)."
                " Defaults to current system time"
            ),
            "example": INDY_ISO8601_DATETIME_EXAMPLE,
        },
    )

    domain = fields.Str(
        required=False,
        metadata={
            "description": "The intended domain of validity for the proof",
            "example": "example.com",
        },
    )

    challenge = fields.Str(
        required=False,
        metadata={
            "description": (
                "A challenge to include in the proof. SHOULD be provided by the"
                " requesting party of the credential (=holder)"
            ),
            "example": UUID4_EXAMPLE,
        },
    )

    credential_status = fields.Nested(
        CredentialStatusOptionsSchema(),
        data_key="credentialStatus",
        required=False,
        metadata={
            "description": (
                "The credential status mechanism to use for the credential. Omitting"
                " the property indicates the issued credential will not include a"
                " credential status"
            )
        },
    )
