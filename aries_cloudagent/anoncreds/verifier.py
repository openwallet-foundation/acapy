"""Indy-Credx verifier implementation."""

import asyncio
import logging
from enum import Enum
from time import time
from typing import List, Mapping, Tuple

from anoncreds import AnoncredsError, Presentation

from ..core.profile import Profile
from ..indy.models.xform import indy_proof_req2non_revoc_intervals
from ..messaging.util import canon, encode
from .models.anoncreds_cred_def import GetCredDefResult
from .registry import AnonCredsRegistry

LOGGER = logging.getLogger(__name__)


class PresVerifyMsg(str, Enum):
    """Credential verification codes."""

    RMV_REFERENT_NON_REVOC_INTERVAL = "RMV_RFNT_NRI"
    RMV_GLOBAL_NON_REVOC_INTERVAL = "RMV_GLB_NRI"
    TSTMP_OUT_NON_REVOC_INTRVAL = "TS_OUT_NRI"
    CT_UNREVEALED_ATTRIBUTES = "UNRVL_ATTR"
    PRES_VALUE_ERROR = "VALUE_ERROR"
    PRES_VERIFY_ERROR = "VERIFY_ERROR"


class AnonCredsVerifier:
    """Verifier class."""

    def __init__(self, profile: Profile):
        """Initialize an AnonCredsVerifier instance.

        Args:
            profile: an active profile instance

        """
        self.profile = profile

    def non_revoc_intervals(self, pres_req: dict, pres: dict, cred_defs: dict) -> list:
        """Remove superfluous non-revocation intervals in presentation request.

        Irrevocable credentials constitute proof of non-revocation, but
        indy rejects proof requests with non-revocation intervals lining up
        with non-revocable credentials in proof: seek and remove.

        Args:
            pres_req: presentation request
            pres: corresponding presentation

        """
        msgs = []
        for req_proof_key, pres_key in {
            "revealed_attrs": "requested_attributes",
            "revealed_attr_groups": "requested_attributes",
            "predicates": "requested_predicates",
        }.items():
            for uuid, spec in pres["requested_proof"].get(req_proof_key, {}).items():
                if (
                    "revocation"
                    not in cred_defs[
                        pres["identifiers"][spec["sub_proof_index"]]["cred_def_id"]
                    ]["value"]
                ):
                    if uuid in pres_req[pres_key] and pres_req[pres_key][uuid].pop(
                        "non_revoked", None
                    ):
                        msgs.append(
                            f"{PresVerifyMsg.RMV_REFERENT_NON_REVOC_INTERVAL.value}::"
                            f"{uuid}"
                        )
                        LOGGER.info(
                            (
                                "Amended presentation request (nonce=%s): removed "
                                "non-revocation interval at %s referent "
                                "%s; corresponding credential in proof is irrevocable"
                            ),
                            pres_req["nonce"],
                            pres_key,
                            uuid,
                        )

        if all(
            (
                spec.get("timestamp") is None
                and "revocation" not in cred_defs[spec["cred_def_id"]]["value"]
            )
            for spec in pres["identifiers"]
        ):
            pres_req.pop("non_revoked", None)
            msgs.append(PresVerifyMsg.RMV_GLOBAL_NON_REVOC_INTERVAL.value)
            LOGGER.warning(
                (
                    "Amended presentation request (nonce=%s); removed global "
                    "non-revocation interval; no revocable credentials in proof"
                ),
                pres_req["nonce"],
            )
        return msgs

    async def check_timestamps(
        self,
        profile: Profile,
        pres_req: Mapping,
        pres: Mapping,
        rev_reg_defs: Mapping,
    ) -> list:
        """Check for suspicious, missing, and superfluous timestamps.

        Raises ValueError on timestamp in the future, prior to rev reg creation,
        superfluous or missing.

        Args:
            profile: relevant profile
            pres_req: indy proof request
            pres: indy proof request
            rev_reg_defs: rev reg defs by rev reg id, augmented with transaction times
        """
        msgs = []
        now = int(time())
        non_revoc_intervals = indy_proof_req2non_revoc_intervals(pres_req)
        LOGGER.debug(f">>> got non-revoc intervals: {non_revoc_intervals}")

        # timestamp for irrevocable credential
        cred_defs: List[GetCredDefResult] = []
        for index, ident in enumerate(pres["identifiers"]):
            LOGGER.debug(f">>> got (index, ident): ({index},{ident})")
            cred_def_id = ident["cred_def_id"]
            anoncreds_registry = profile.inject(AnonCredsRegistry)
            cred_def_result = await anoncreds_registry.get_credential_definition(
                profile, cred_def_id
            )
            cred_defs.append(cred_def_result)
            if ident.get("timestamp"):
                if not cred_def_result.credential_definition.value.revocation:
                    raise ValueError(
                        f"Timestamp in presentation identifier #{index} "
                        f"for irrevocable cred def id {cred_def_id}"
                    )

        # timestamp in the future too far in the past
        for ident in pres["identifiers"]:
            timestamp = ident.get("timestamp")
            rev_reg_id = ident.get("rev_reg_id")

            if not timestamp:
                continue

            if timestamp > now + 300:  # allow 5 min for clock skew
                raise ValueError(f"Timestamp {timestamp} is in the future")
            reg_def = rev_reg_defs.get(rev_reg_id)
            if not reg_def:
                raise ValueError(f"Missing registry definition for '{rev_reg_id}'")
            # TODO Generic anoncreds rev reg def does not include txn time or similar
            # if "txnTime" not in reg_def:
            #     raise ValueError(
            #         f"Missing txnTime for registry definition '{rev_reg_id}'"
            #     )
            # if timestamp < reg_def["txnTime"]:
            #     raise ValueError(
            #         f"Timestamp {timestamp} predates rev reg {rev_reg_id} creation"
            #     )

        # timestamp superfluous, missing, or outside non-revocation interval
        revealed_attrs = pres["requested_proof"].get("revealed_attrs", {})
        unrevealed_attrs = pres["requested_proof"].get("unrevealed_attrs", {})
        revealed_groups = pres["requested_proof"].get("revealed_attr_groups", {})
        self_attested = pres["requested_proof"].get("self_attested_attrs", {})
        preds = pres["requested_proof"].get("predicates", {})
        for uuid, req_attr in pres_req["requested_attributes"].items():
            if "name" in req_attr:
                if uuid in revealed_attrs:
                    index = revealed_attrs[uuid]["sub_proof_index"]
                    if cred_defs[index].credential_definition.value.revocation:
                        timestamp = pres["identifiers"][index].get("timestamp")
                        if (timestamp is not None) ^ bool(
                            non_revoc_intervals.get(uuid)
                        ):
                            LOGGER.debug(f">>> uuid: {uuid}")
                            LOGGER.debug(
                                f">>> revealed_attrs[uuid]: {revealed_attrs[uuid]}"
                            )
                            raise ValueError(
                                f"Timestamp on sub-proof #{index} "
                                f"is {'superfluous' if timestamp else 'missing'} "
                                f"vs. requested attribute {uuid}"
                            )
                        if non_revoc_intervals.get(uuid) and not (
                            non_revoc_intervals[uuid].get("from", 0)
                            < timestamp
                            < non_revoc_intervals[uuid].get("to", now)
                        ):
                            msgs.append(
                                f"{PresVerifyMsg.TSTMP_OUT_NON_REVOC_INTRVAL.value}::"
                                f"{uuid}"
                            )
                            LOGGER.info(
                                f"Timestamp {timestamp} from ledger for item"
                                f"{uuid} falls outside non-revocation interval "
                                f"{non_revoc_intervals[uuid]}"
                            )
                elif uuid in unrevealed_attrs:
                    # nothing to do, attribute value is not revealed
                    msgs.append(
                        f"{PresVerifyMsg.CT_UNREVEALED_ATTRIBUTES.value}::" f"{uuid}"
                    )
                elif uuid not in self_attested:
                    raise ValueError(
                        f"Presentation attributes mismatch requested attribute {uuid}"
                    )

            elif "names" in req_attr:
                group_spec = revealed_groups.get(uuid)
                if (
                    group_spec is None
                    or "sub_proof_index" not in group_spec
                    or "values" not in group_spec
                ):
                    raise ValueError(f"Missing requested attribute group {uuid}")
                index = group_spec["sub_proof_index"]
                if cred_defs[index].credential_definition.value.revocation:
                    timestamp = pres["identifiers"][index].get("timestamp")
                    if (timestamp is not None) ^ bool(non_revoc_intervals.get(uuid)):
                        raise ValueError(
                            f"Timestamp on sub-proof #{index} "
                            f"is {'superfluous' if timestamp else 'missing'} "
                            f"vs. requested attribute group {uuid}"
                        )
                    if non_revoc_intervals.get(uuid) and not (
                        non_revoc_intervals[uuid].get("from", 0)
                        < timestamp
                        < non_revoc_intervals[uuid].get("to", now)
                    ):
                        msgs.append(
                            f"{PresVerifyMsg.TSTMP_OUT_NON_REVOC_INTRVAL.value}::"
                            f"{uuid}"
                        )
                        LOGGER.warning(
                            f"Timestamp {timestamp} from ledger for item"
                            f"{uuid} falls outside non-revocation interval "
                            f"{non_revoc_intervals[uuid]}"
                        )

        for uuid, req_pred in pres_req["requested_predicates"].items():
            pred_spec = preds.get(uuid)
            if pred_spec is None or "sub_proof_index" not in pred_spec:
                raise ValueError(
                    f"Presentation predicates mismatch requested predicate {uuid}"
                )
            index = pred_spec["sub_proof_index"]
            if cred_defs[index].credential_definition.value.revocation:
                timestamp = pres["identifiers"][index].get("timestamp")
                if (timestamp is not None) ^ bool(non_revoc_intervals.get(uuid)):
                    raise ValueError(
                        f"Timestamp on sub-proof #{index} "
                        f"is {'superfluous' if timestamp else 'missing'} "
                        f"vs. requested predicate {uuid}"
                    )
                if non_revoc_intervals.get(uuid) and not (
                    non_revoc_intervals[uuid].get("from", 0)
                    < timestamp
                    < non_revoc_intervals[uuid].get("to", now)
                ):
                    msgs.append(
                        f"{PresVerifyMsg.TSTMP_OUT_NON_REVOC_INTRVAL.value}::" f"{uuid}"
                    )
                    LOGGER.warning(
                        f"Best-effort timestamp {timestamp} "
                        "from ledger falls outside non-revocation interval "
                        f"{non_revoc_intervals[uuid]}"
                    )
        return msgs

    async def pre_verify(self, pres_req: dict, pres: dict) -> list:
        """Check for essential components and tampering in presentation.

        Visit encoded attribute values against raw, and predicate bounds,
        in presentation, cross-reference against presentation request.

        Args:
            pres_req: presentation request
            pres: corresponding presentation

        """
        msgs = []
        if not (
            pres_req
            and "requested_predicates" in pres_req
            and "requested_attributes" in pres_req
        ):
            raise ValueError("Incomplete or missing proof request")
        if not pres:
            raise ValueError("No proof provided")
        if "requested_proof" not in pres:
            raise ValueError("Presentation missing 'requested_proof'")
        if "proof" not in pres:
            raise ValueError("Presentation missing 'proof'")

        for uuid, req_pred in pres_req["requested_predicates"].items():
            try:
                canon_attr = canon(req_pred["name"])
                matched = False
                found = False
                pred = None
                for ge_proof in pres["proof"]["proofs"][
                    pres["requested_proof"]["predicates"][uuid]["sub_proof_index"]
                ]["primary_proof"]["ge_proofs"]:
                    pred = ge_proof["predicate"]
                    if pred["attr_name"] == canon_attr:
                        found = True
                        if pred["value"] == req_pred["p_value"]:
                            matched = True
                            break
                if not matched:
                    raise ValueError(f"Predicate not found: {canon_attr}")
                elif not found:
                    raise ValueError(f"Missing requested predicate '{uuid}'")
            except (KeyError, TypeError):
                raise ValueError(f"Missing requested predicate '{uuid}'")

        revealed_attrs = pres["requested_proof"].get("revealed_attrs", {})
        unrevealed_attrs = pres["requested_proof"].get("unrevealed_attrs", {})
        revealed_groups = pres["requested_proof"].get("revealed_attr_groups", {})
        self_attested = pres["requested_proof"].get("self_attested_attrs", {})
        for uuid, req_attr in pres_req["requested_attributes"].items():
            if "name" in req_attr:
                if uuid in revealed_attrs:
                    pres_req_attr_spec = {req_attr["name"]: revealed_attrs[uuid]}
                elif uuid in unrevealed_attrs:
                    # unrevealed attribute, nothing to do
                    pres_req_attr_spec = {}
                    msgs.append(
                        f"{PresVerifyMsg.CT_UNREVEALED_ATTRIBUTES.value}::" f"{uuid}"
                    )
                elif uuid in self_attested:
                    if not req_attr.get("restrictions"):
                        continue
                    raise ValueError(
                        "Attribute with restrictions cannot be self-attested: "
                        f"'{req_attr['name']}'"
                    )
                else:
                    raise ValueError(
                        f"Missing requested attribute '{req_attr['name']}'"
                    )
            elif "names" in req_attr:
                group_spec = revealed_groups[uuid]
                pres_req_attr_spec = {
                    attr: {
                        "sub_proof_index": group_spec["sub_proof_index"],
                        **group_spec["values"].get(attr),
                    }
                    for attr in req_attr["names"]
                }
            else:
                raise ValueError(
                    f"Request attribute missing 'name' and 'names': '{uuid}'"
                )

            for attr, spec in pres_req_attr_spec.items():
                try:
                    primary_enco = pres["proof"]["proofs"][spec["sub_proof_index"]][
                        "primary_proof"
                    ]["eq_proof"]["revealed_attrs"][canon(attr)]
                except (KeyError, TypeError):
                    raise ValueError(f"Missing revealed attribute: '{attr}'")
                if primary_enco != spec["encoded"]:
                    raise ValueError(f"Encoded representation mismatch for '{attr}'")
                if primary_enco != encode(spec["raw"]):
                    raise ValueError(f"Encoded representation mismatch for '{attr}'")
        return msgs

    async def process_pres_identifiers(
        self,
        identifiers: list,
    ) -> Tuple[dict, dict, dict, dict]:
        """Return schemas, cred_defs, rev_reg_defs, rev_lists."""
        schema_ids = []
        cred_def_ids = []

        schemas = {}
        cred_defs = {}
        rev_reg_defs = {}
        rev_lists = {}

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
                    rev_lists.setdefault(identifier["rev_reg_id"], {})

                    if (
                        identifier["timestamp"]
                        not in rev_lists[identifier["rev_reg_id"]]
                    ):
                        result = await anoncreds_registry.get_revocation_list(
                            self.profile,
                            identifier["rev_reg_id"],
                            identifier["timestamp"],
                        )
                        rev_lists[identifier["rev_reg_id"]][
                            identifier["timestamp"]
                        ] = result.revocation_list.serialize()
        return (
            schemas,
            cred_defs,
            rev_reg_defs,
            rev_lists,
        )

    async def verify_presentation(
        self,
        pres_req,
        pres,
        schemas,
        credential_definitions,
        rev_reg_defs,
        rev_lists,
    ) -> Tuple[bool, list]:
        """Verify a presentation.

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
                [
                    rev_list
                    for timestamp_to_list in rev_lists.values()
                    for rev_list in timestamp_to_list.values()
                ],
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
