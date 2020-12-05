"""Indy SDK verifier implementation."""

import json
import logging

import indy.anoncreds
from indy.error import IndyError

from ...ledger.indy import IndySdkLedger

from ..verifier import IndyVerifier, PreVerifyResult

LOGGER = logging.getLogger(__name__)


class IndySdkVerifier(IndyVerifier):
    """Indy verifier class."""

    def __init__(self, ledger: IndySdkLedger):
        """
        Initialize an IndyVerifier instance.

        Args:
            ledger: ledger instance

        """
        self.ledger = ledger

    async def verify_presentation(
        self,
        presentation_request,
        presentation,
        schemas,
        credential_definitions,
        rev_reg_defs,
        rev_reg_entries,
    ) -> bool:
        """
        Verify a presentation.

        Args:
            presentation_request: Presentation request data
            presentation: Presentation data
            schemas: Schema data
            credential_definitions: credential definition data
            rev_reg_defs: revocation registry definitions
            rev_reg_entries: revocation registry entries
        """

        self.non_revoc_intervals(presentation_request, presentation)

        (pv_result, pv_msg) = await self.pre_verify(presentation_request, presentation)
        if pv_result != PreVerifyResult.OK:
            LOGGER.error(
                f"Presentation on nonce={presentation_request['nonce']} "
                f"cannot be validated: {pv_result.value} [{pv_msg}]"
            )
            return False

        try:
            verified = await indy.anoncreds.verifier_verify_proof(
                json.dumps(presentation_request),
                json.dumps(presentation),
                json.dumps(schemas),
                json.dumps(credential_definitions),
                json.dumps(rev_reg_defs),
                json.dumps(rev_reg_entries),
            )
        except IndyError:
            LOGGER.exception(
                f"Validation of presentation on nonce={presentation_request['nonce']} "
                "failed with error"
            )
            verified = False

        return verified
