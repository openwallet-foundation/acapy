"""Verifiable Credential model classes"""

from marshmallow import ValidationError
import copy
import json
from typing import List, Optional, Union
from datetime import datetime

from ....messaging.valid import Uri
from ...ld_proofs.constants import (
    CREDENTIALS_CONTEXT_V1_URL,
    VERIFIABLE_CREDENTIAL_TYPE,
)
from .credential_schema import (
    CredentialSchema,
    VerifiableCredentialSchema,
    LinkedDataProofSchema,
)


class LDProof:
    """Linked Data Proof model."""

    def __init__(
        self,
        type: Optional[str] = None,
        proof_purpose: Optional[str] = None,
        verification_method: Optional[str] = None,
        created: Optional[str] = None,
        domain: Optional[str] = None,
        challenge: Optional[str] = None,
        jws: Optional[str] = None,
        proof_value: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Initialize the LDProof instance."""

        self.type = type
        self.proof_purpose = proof_purpose
        self.verification_method = verification_method
        self.created = created
        self.domain = domain
        self.challenge = challenge
        self.jws = jws
        self.proof_value = proof_value
        self.extra = kwargs

    @classmethod
    def deserialize(cls, proof: Union[dict, str]) -> "LDProof":
        """Deserialize a dict into a LDProof object.

        Args:
            proof: proof

        Returns:
            LDProof: The deserialized LDProof object

        """
        if isinstance(proof, str):
            proof = json.loads(proof)
        schema = LinkedDataProofSchema()
        proof = schema.load(proof)
        return proof

    def serialize(self) -> dict:
        """Serialize the LDProof object into dict.

        Returns:
            dict: The LDProof serialized as dict.

        """
        schema = LinkedDataProofSchema()
        proof: dict = schema.dump(copy.deepcopy(self))
        proof.update(self.extra)
        return proof


class VerifiableCredential:
    """Verifiable Credential model."""

    def __init__(
        self,
        context: Optional[List[Union[str, dict]]] = None,
        id: Optional[str] = None,
        type: Optional[List[str]] = None,
        issuer: Optional[Union[dict, str]] = None,
        issuance_date: Optional[str] = None,
        expiration_date: Optional[str] = None,
        credential_subject: Optional[Union[dict, List[dict]]] = None,
        proof: Optional[Union[dict, LDProof]] = None,
        **kwargs,
    ) -> None:
        """Initialize the VerifiableCredential instance."""
        self._context = context or [CREDENTIALS_CONTEXT_V1_URL]
        self._id = id
        self._type = type or [VERIFIABLE_CREDENTIAL_TYPE]
        self._issuer = issuer
        self._credential_subject = credential_subject

        # TODO: proper date parsing
        self._issuance_date = issuance_date
        self._expiration_date = expiration_date

        if isinstance(proof, dict):
            proof = LDProof.deserialize(proof)
        self._proof = proof

        self.extra = kwargs

    @classmethod
    def deserialize(
        cls, credential: Union[dict, str], without_proof=False
    ) -> "VerifiableCredential":
        """Deserialize a dict into a VerifiableCredential object.

        Args:
            credential: The credential to deserialize
            without_proof: To deserialize without checking for required proof property

        Returns:
            VerifiableCredential: The deserialized VerifiableCredential object

        """
        if isinstance(credential, str):
            credential = json.loads(credential)
        schema = CredentialSchema() if without_proof else VerifiableCredentialSchema()
        credential = schema.load(credential)
        return credential

    def serialize(self) -> dict:
        """Serialize the VerifiableCredential object into dict.

        Returns:
            dict: The VerifiableCredential serialized as dict.

        """
        schema = VerifiableCredentialSchema()
        credential: dict = schema.dump(copy.deepcopy(self))
        credential.update(self.extra)
        return credential

    @property
    def context(self):
        """Getter for context."""
        return self._context

    @context.setter
    def context(self, context: List[Union[str, dict]]):
        """Setter for context.

        First item must be credentials v1 url
        """
        assert context[0] == CREDENTIALS_CONTEXT_V1_URL

        self._context = context

    def add_context(self, context: Union[str, dict]):
        """Add a context to this credential."""
        self._context.append(context)

    @property
    def context_urls(self) -> List[str]:
        """Getter for context urls."""
        return [context for context in self.context if type(context) is str]

    @property
    def type(self) -> List[str]:
        """Getter for type."""
        return self._type

    @type.setter
    def type(self, type: List[str]):
        """Setter for type.

        First item must be VerifiableCredential
        """
        assert type[0] == VERIFIABLE_CREDENTIAL_TYPE

        self._type = type

    def add_type(self, type: str):
        """Add a type to this credential."""
        self._type.append(type)

    @property
    def id(self):
        """Getter for id."""
        return self._id

    @id.setter
    def id(self, id: Union[str]):
        """Setter for id."""
        if id:
            uri_validator = Uri()
            uri_validator(id)

        self._id = id

    @property
    def issuer_id(self) -> Optional[str]:
        """Getter for issuer id."""
        if not self._issuer:
            return None
        elif type(self._issuer) is str:
            return self._issuer

        return self._issuer.get("id")

    @issuer_id.setter
    def issuer_id(self, issuer_id: str):
        """Setter for issuer id."""
        uri_validator = Uri()
        uri_validator(issuer_id)

        # Use simple string variant if possible
        if not self._issuer or isinstance(self._issuer, str):
            self._issuer = issuer_id
        else:
            self._issuer["id"] = issuer_id

    @property
    def issuer(self):
        """Getter for issuer."""
        return self._issuer

    @issuer.setter
    def issuer(self, issuer: Union[str, dict]):
        """Setter for issuer."""
        uri_validator = Uri()

        issuer_id = issuer if isinstance(issuer, str) else issuer.get("issuer_id")

        if not issuer_id:
            raise ValidationError("Issuer id is required")
        uri_validator(issuer_id)

        self._issuer = issuer

    @property
    def issuance_date(self):
        """Getter for issuance date."""
        return self._issuance_date

    @issuance_date.setter
    def issuance_date(self, date: Union[str, datetime]):
        """Setter for issuance date."""
        if isinstance(date, datetime):
            date = date.isoformat()

        self._issuance_date = date

    @property
    def expiration_date(self):
        """Getter for expiration date."""
        return self._expiration_date

    @expiration_date.setter
    def expiration_date(self, date: Union[str, datetime, None]):
        """Setter for expiration date."""
        if isinstance(date, datetime):
            date = date.isoformat()

        self._expiration_date = date

    @property
    def credential_subject_ids(self) -> List[str]:
        """Getter for credential subject ids."""
        if not self._credential_subject:
            return []
        elif type(self._credential_subject) is dict:
            subject_id = self._credential_subject.get("id")

            return [subject_id] if subject_id else []
        else:
            return [
                subject.get("id")
                for subject in self._credential_subject
                if subject.get("id")
            ]

    @property
    def credential_subject(self):
        """Getter for credential subject."""
        return self._credential_subject

    @credential_subject.setter
    def credential_subject(self, credential_subject: Union[dict, List[dict]]):
        """Setter for credential subject."""

        uri_validator = Uri()

        subjects = (
            [credential_subject]
            if isinstance(credential_subject, dict)
            else credential_subject
        )

        # loop trough all credential subjects and check for valid id uri
        for subject in subjects:
            if subject.get("id"):
                uri_validator(subject.get("id"))

        self._credential_subject = credential_subject

    @property
    def proof(self):
        """Getter for proof."""
        return self._proof

    @proof.setter
    def proof(self, proof: LDProof):
        """Setter for proof."""
        self._proof = proof
