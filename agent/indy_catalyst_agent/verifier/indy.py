"""Indy verifier implementation."""

import json
import logging

import indy.anoncreds

from .base import BaseVerifier


class IndyVerifier(BaseVerifier):
    """Indy holder class."""

    def __init__(self, wallet):
        """
        Initialize an IndyHolder instance.

        Args:
            wallet: IndyWallet instance

        """
        self.logger = logging.getLogger(__name__)
        self.wallet = wallet

    async def verify_presentation(
        self, presentation_request, presentation, schemas, credential_definitions
    ) -> bool:
        """
        Verify a presentation.

        Args:
            presentation_request: Presentation request data
            presentation: Presentation data
            schemas: Schema data
            credential_definitions: credential definition data
        """

        verified = await indy.anoncreds.verifier_verify_proof(
            json.dumps(presentation_request),
            json.dumps(presentation),
            json.dumps(schemas),
            json.dumps(credential_definitions),
            json.dumps({}),  # no revocation
            json.dumps({}),
        )

        return verified
