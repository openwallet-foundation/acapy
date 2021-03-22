"""Linked data proof verifiable options detail artifacts to attach to RFC 453 messages."""


import copy
import json
from typing import Optional, Union


from .......vc.vc_ld.models.credential import (
    VerifiableCredential,
)
from .cred_detail_schema import LDProofVCDetailOptionsSchema, LDProofVCDetailSchema


class LDProofVCDetailOptions:
    """Linked Data Proof verifiable credential options model"""

    def __init__(
        self,
        proof_type: Optional[str] = None,
        proof_purpose: Optional[str] = None,
        created: Optional[str] = None,
        domain: Optional[str] = None,
        challenge: Optional[str] = None,
        credential_status: Optional[dict] = None,
        **kwargs,
    ) -> None:
        """Initialize the LDProofVCDetailOptions instance."""

        self.proof_type = proof_type
        self.proof_purpose = proof_purpose
        self.created = created
        self.domain = domain
        self.challenge = challenge
        self.credential_status = credential_status
        self.extra = kwargs

    @classmethod
    def deserialize(cls, detail_options: Union[dict, str]) -> "LDProofVCDetailOptions":
        """Deserialize a dict into a LDProofVCDetailOptions object.

        Args:
            detail_options: detail_options

        Returns:
            LDProofVCDetailOptions: The deserialized LDProofVCDetailOptions object
        """
        if isinstance(detail_options, str):
            detail_options = json.loads(detail_options)
        schema = LDProofVCDetailOptionsSchema()
        detail_options = schema.load(detail_options)
        return detail_options

    def serialize(self) -> dict:
        """Serialize the LDProofVCDetailOptions object into dict.

        Returns:
            dict: The LDProofVCDetailOptions serialized as dict.
        """
        schema = LDProofVCDetailOptionsSchema()
        detail_options: dict = schema.dump(copy.deepcopy(self))
        detail_options.update(self.extra)
        return detail_options


class LDProofVCDetail:
    """Linked data proof verifiable credential detail."""

    def __init__(
        self,
        credential: Optional[Union[dict, VerifiableCredential]],
        options: Optional[Union[dict, LDProofVCDetailOptions]],
    ) -> None:
        if isinstance(credential, dict):
            credential = VerifiableCredential.deserialize(credential)
        self.credential = credential

        if isinstance(options, dict):
            options = LDProofVCDetailOptions.deserialize(options)
        self.options = options

    @classmethod
    def deserialize(cls, detail: Union[dict, str]) -> "LDProofVCDetail":
        """Deserialize a dict into a LDProofVCDetail object.

        Args:
            detail: detail

        Returns:
            LDProofVCDetail: The deserialized LDProofVCDetail object
        """
        if isinstance(detail, str):
            detail = json.loads(detail)
        schema = LDProofVCDetailSchema()
        detail = schema.load(detail)
        return detail

    def serialize(self) -> dict:
        """Serialize the LDProofVCDetail object into dict.

        Returns:
            dict: The LDProofVCDetail serialized as dict.
        """
        schema = LDProofVCDetailSchema()
        detail: dict = schema.dump(copy.deepcopy(self))
        return detail

    def __eq__(self, other: object) -> bool:
        """Comparison between linked data vc details."""
        if isinstance(other, LDProofVCDetail):
            return self.credential == other.credential and self.options == other.options
        return False
