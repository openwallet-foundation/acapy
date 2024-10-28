"""DataIntegrityProof."""

from typing import Optional

from marshmallow import INCLUDE, fields, post_dump

from ....messaging.models.base import BaseModel, BaseModelSchema
from ....messaging.valid import (
    RFC3339_DATETIME_EXAMPLE,
    UUID4_EXAMPLE,
    Uri,
)


class DataIntegrityProof(BaseModel):
    """Data Integrity Proof model."""

    class Meta:
        """DataIntegrityProof metadata."""

        schema_class = "DataIntegrityProofSchema"

    def __init__(
        self,
        id: Optional[str] = None,
        type: Optional[str] = "DataIntegrityProof",
        proof_purpose: Optional[str] = None,
        verification_method: Optional[str] = None,
        cryptosuite: Optional[str] = None,
        created: Optional[str] = None,
        expires: Optional[str] = None,
        domain: Optional[str] = None,
        challenge: Optional[str] = None,
        proof_value: Optional[str] = None,
        previous_proof: Optional[str] = None,
        nonce: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Initialize the DataIntegrityProof instance."""

        self.id = id
        self.type = type
        self.proof_purpose = proof_purpose
        self.verification_method = verification_method
        self.cryptosuite = cryptosuite
        self.created = created
        self.expires = expires
        self.domain = domain
        self.challenge = challenge
        self.proof_value = proof_value
        self.previous_proof = previous_proof
        self.nonce = nonce
        self.extra = kwargs


class DataIntegrityProofSchema(BaseModelSchema):
    """Data Integrity Proof schema.

    Based on https://www.w3.org/TR/vc-data-integrity/#proofs

    """

    class Meta:
        """Accept parameter overload."""

        unknown = INCLUDE
        model_class = DataIntegrityProof

    id = fields.Str(
        required=False,
        metadata={
            "description": (
                "An optional identifier for the proof, which MUST be a URL [URL], "
                "such as a UUID as a URN"
            ),
            "example": "urn:uuid:6a1676b8-b51f-11ed-937b-d76685a20ff5",
        },
    )

    type = fields.Str(
        required=True,
        metadata={
            "description": (
                "The specific type of proof MUST be specified as a string that maps "
                "to a URL [URL]."
            ),
            "example": "DataIntegrityProof",
        },
    )

    proof_purpose = fields.Str(
        data_key="proofPurpose",
        required=True,
        metadata={
            "description": (
                "The proof purpose acts as a safeguard to prevent the proof "
                "from being misused by being applied to a purpose other than the one "
                "that was intended."
            ),
            "example": "assertionMethod",
        },
    )

    verification_method = fields.Str(
        data_key="verificationMethod",
        required=True,
        validate=Uri(),
        metadata={
            "description": (
                "A verification method is the means and information needed "
                "to verify the proof."
            ),
            "example": (
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg34"
                "2Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ),
        },
    )

    cryptosuite = fields.Str(
        required=True,
        metadata={
            "description": (
                "An identifier for the cryptographic suite that can be used to verify "
                "the proof."
            ),
            "example": "eddsa-jcs-2022",
        },
    )

    created = fields.Str(
        required=False,
        metadata={
            "description": (
                "The date and time the proof was created is OPTIONAL and, if included, "
                "MUST be specified as an [XMLSCHEMA11-2] dateTimeStamp string"
            ),
            "example": RFC3339_DATETIME_EXAMPLE,
        },
    )

    expires = fields.Str(
        required=False,
        metadata={
            "description": (
                "The expires property is OPTIONAL and, if present, specifies when the "
                "proof expires. If present, it MUST be an [XMLSCHEMA11-2] "
                "dateTimeStamp string"
            ),
            "example": RFC3339_DATETIME_EXAMPLE,
        },
    )

    domain = fields.Str(
        required=False,
        metadata={
            "description": (
                "It conveys one or more security domains in which the proof is "
                "meant to be used."
            ),
            "example": "example.com",
        },
    )

    challenge = fields.Str(
        required=False,
        metadata={
            "description": (
                "The value is used once for a particular domain and window of time. "
                "This value is used to mitigate replay attacks."
            ),
            "example": UUID4_EXAMPLE,
        },
    )

    proof_value = fields.Str(
        required=False,
        data_key="proofValue",
        metadata={
            "description": (
                "A string value that expresses base-encoded binary data necessary "
                "to verify the digital proof using the verificationMethod specified."
            ),
            "example": (
                "zsy1AahqbzJQ63n9RtekmwzqZeVj494VppdAVJBnMYrTwft6cLJJGeTSSxCCJ6HKnR"
                "twE7jjDh6sB2z2AAiZY9BBnCD8wUVgwqH3qchGRCuC2RugA4eQ9fUrR4Yuycac3caiaaay"
            ),
        },
    )

    previous_proof = fields.Str(
        required=False,
        data_key="previousProof",
        metadata={
            "description": (
                "Each value identifies another data integrity proof that "
                "MUST verify before the current proof is processed."
            ),
            "example": ("urn:uuid:6a1676b8-b51f-11ed-937b-d76685a20ff5"),
        },
    )

    nonce = fields.Str(
        required=False,
        metadata={
            "description": (
                "One use of this field is to increase privacy by decreasing linkability "
                "that is the result of deterministically generated signatures."
            ),
            "example": (
                "CF69iO3nfvqRsRBNElE8b4wO39SyJHPM7Gg1nExltW5vSfQA1lvDCR/zXX1To0/4NLo=="
            ),
        },
    )

    @post_dump(pass_original=True)
    def add_unknown_properties(self, data: dict, original, **kwargs):
        """Add back unknown properties before outputting."""

        data.update(original.extra)

        return data
