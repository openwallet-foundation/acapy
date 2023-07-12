"""Indy-Credx verifier implementation."""

import asyncio
import logging

from typing import Tuple

from indy_credx import CredxError, Presentation

from ...core.profile import Profile

from ..verifier import IndyVerifier, PresVerifyMsg

LOGGER = logging.getLogger(__name__)


class IndyCredxVerifier(IndyVerifier):
    """Indy-Credx verifier class."""

    def __init__(self, profile: Profile):
        """
        Initialize an IndyCredxVerifier instance.

        Args:
            profile: an active profile instance

        """
        self.profile = profile

    async def verify_presentation(
        self,
        pres_req,
        pres,
        schemas,
        credential_definitions,
        rev_reg_defs,
        rev_reg_entries,
    ) -> Tuple[bool, list]:
        """
        Verify a presentation.

        Args:
            pres_req: Presentation request data
            pres: Presentation data
            schemas: Schema data
            credential_definitions: credential definition data
            rev_reg_defs: revocation registry definitions
            rev_reg_entries: revocation registry entries
        """

        accept_legacy_revocation = (
            self.profile.settings.get("revocation.anoncreds_legacy_support", "accept")
            == "accept"
        )
        msgs = []
        try:
            msgs += self.non_revoc_intervals(pres_req, pres, credential_definitions)
            msgs += await self.check_timestamps(
                self.profile, pres_req, pres, rev_reg_defs
            )
            msgs += await self.pre_verify(pres_req, pres)
        except ValueError as err:
            s = str(err)
            msgs.append(f"{PresVerifyMsg.PRES_VALUE_ERROR.value}::{s}")
            LOGGER.error(
                f"Presentation on nonce={pres_req['nonce']} "
                f"cannot be validated: {str(err)}"
            )
            return (False, msgs)

        try:
            presentation = Presentation.load(pres)
            verified = await asyncio.get_event_loop().run_in_executor(
                None,
                presentation.verify,
                pres_req,
                schemas.values(),
                credential_definitions.values(),
                rev_reg_defs.values(),
                rev_reg_entries,
                accept_legacy_revocation,
            )
        except CredxError as err:
            s = str(err)
            msgs.append(f"{PresVerifyMsg.PRES_VERIFY_ERROR.value}::{s}")
            LOGGER.exception(
                f"Validation of presentation on nonce={pres_req['nonce']} "
                "failed with error"
            )
            verified = False

        return (verified, msgs)
