"""Indy-Credx verifier implementation."""

import asyncio
import logging
from typing import Tuple

from anoncreds import AnoncredsError, Presentation

from aries_cloudagent.anoncreds.anoncreds.anoncreds_registry import AnonCredsRegistry

from ...core.profile import Profile

from ..verifier import AnonCredsVerifier, PresVerifyMsg

LOGGER = logging.getLogger(__name__)


class AnonCredsRsVerifier(AnonCredsVerifier):
    """Verifier class."""

    def __init__(self, profile: Profile):
        """
        Initialize an AnonCredsRsVerifier instance.

        Args:
            profile: an active profile instance

        """
        self.profile = profile

    async def process_pres_identifiers(
        self,
        identifiers: list,
    ) -> Tuple[dict, dict, dict, dict]:
        """Return schemas, cred_defs, rev_reg_defs, rev_status_lists."""
        schema_ids = []
        cred_def_ids = []

        schemas = {}
        cred_defs = {}
        rev_reg_defs = {}
        rev_status_lists = {}

        for identifier in identifiers:
            schema_ids.append(identifier["schema_id"])
            cred_def_ids.append(identifier["cred_def_id"])

            anoncreds_registry = self.profile.inject(AnonCredsRegistry)
            # Build schemas for anoncreds
            if identifier["schema_id"] not in schemas:
                schemas[identifier["schema_id"]] = (
                    await anoncreds_registry.get_schema(
                        self.profile, identifier["schema_id"]
                    )
                ).schema.serialize()
            if identifier["cred_def_id"] not in cred_defs:
                cred_defs[identifier["cred_def_id"]] = (
                    await anoncreds_registry.get_credential_definition(
                        self.profile, identifier["cred_def_id"]
                    )
                ).credential_definition.serialize()

            if identifier.get("rev_reg_id"):
                if identifier["rev_reg_id"] not in rev_reg_defs:
                    rev_reg_defs[identifier["rev_reg_id"]] = (
                        await anoncreds_registry.get_revocation_registry_definition(
                            self.profile, identifier["rev_reg_id"]
                        )
                    ).revocation_registry.serialize()

                if identifier.get("timestamp"):
                    rev_status_lists.setdefault(identifier["rev_reg_id"], {})

                    if (
                        identifier["timestamp"]
                        not in rev_status_lists[identifier["rev_reg_id"]]
                    ):
                        result = await anoncreds_registry.get_revocation_status_list(
                            self.profile,
                            identifier["rev_reg_id"],
                            identifier["timestamp"],
                        )
                        rev_status_lists[identifier["rev_reg_id"]][
                            identifier["timestamp"]
                        ] = result.revocation_list.serialize()
        return (
            schemas,
            cred_defs,
            rev_reg_defs,
            rev_status_lists,
        )

    async def verify_presentation(
        self,
        pres_req,
        pres,
        schemas,
        credential_definitions,
        rev_reg_defs,
        rev_status_lists,
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
                schemas,
                credential_definitions,
                rev_reg_defs,
                rev_status_lists,
            )
        except AnoncredsError as err:
            s = str(err)
            msgs.append(f"{PresVerifyMsg.PRES_VERIFY_ERROR.value}::{s}")
            LOGGER.exception(
                f"Validation of presentation on nonce={pres_req['nonce']} "
                "failed with error"
            )
            verified = False

        return (verified, msgs)
