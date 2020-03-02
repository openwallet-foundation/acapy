"""Indy verifier implementation."""

from enum import Enum
import json
import logging

import indy.anoncreds

from ..messaging.util import canon, encode
from .base import BaseVerifier

LOGGER = logging.getLogger(__name__)


class PreVerifyResult(Enum):
    """Represent the result of IndyVerifier.pre_verify."""

    OK = "ok"
    INCOMPLETE = "missing essential components"
    ENCODING_MISMATCH = "demonstrates tampering with raw values"


class IndyVerifier(BaseVerifier):
    """Indy holder class."""

    def __init__(self, wallet):
        """
        Initialize an IndyHolder instance.

        Args:
            wallet: IndyWallet instance

        """
        self.wallet = wallet

    @staticmethod
    def pre_verify(pres_req: dict, pres: dict) -> PreVerifyResult:
        """
        Check for essential components and tampering in presentation.

        Visit encoded attribute values against raw, and predicate bounds,
        in presentation, cross-reference against presentation request.

        Args:
            pres_req: presentation request
            pres: corresponding presentation

        Returns:
            An instance of `PreVerifyResult` representing the validation result

        """
        if not pres:
            LOGGER.debug("No proof provided")
            return PreVerifyResult.INCOMPLETE
        if "requested_proof" not in pres:
            LOGGER.debug("Missing 'requested_proof'")
            return PreVerifyResult.INCOMPLETE
        if "proof" not in pres:
            LOGGER.debug("Missing 'proof'")
            return PreVerifyResult.INCOMPLETE

        for (uuid, req_pred) in pres_req["requested_predicates"].items():
            canon_attr = canon(req_pred["name"])
            try:
                for ge_proof in pres["proof"]["proofs"][
                    pres["requested_proof"]["predicates"][uuid]["sub_proof_index"]
                ]["primary_proof"]["ge_proofs"]:
                    pred = ge_proof["predicate"]
                    if pred["attr_name"] == canon_attr:
                        if pred["value"] != req_pred["p_value"]:
                            LOGGER.debug("Predicate value != p_value")
                            return PreVerifyResult.INCOMPLETE
                        break
                else:
                    LOGGER.debug("Missing requested predicate '%s'", uuid)
                    return PreVerifyResult.INCOMPLETE
            except (KeyError, TypeError):
                LOGGER.debug("Missing requested predicate '%s'", uuid)
                return PreVerifyResult.INCOMPLETE

        revealed_attrs = pres["requested_proof"].get("revealed_attrs", {})
        revealed_groups = pres["requested_proof"].get("revealed_attr_groups", {})
        self_attested = pres["requested_proof"].get("self_attested_attrs", {})
        for (uuid, req_attr) in pres_req["requested_attributes"].items():
            if "name" in req_attr:
                if uuid in revealed_attrs:
                    pres_req_attr_spec = {req_attr["name"]: revealed_attrs[uuid]}
                elif uuid in self_attested:
                    continue
                else:
                    LOGGER.debug("Missing requested attribute '%s'", req_attr["name"])
                    return PreVerifyResult.INCOMPLETE
            elif "names" in req_attr:
                group_spec = revealed_groups.get(uuid)
                if (
                    group_spec is None
                    or "sub_proof_index" not in group_spec
                    or "values" not in group_spec
                ):
                    LOGGER.debug("Missing requested attribute group '%s'", uuid)
                    return PreVerifyResult.INCOMPLETE
                pres_req_attr_spec = {
                    attr: {
                        "sub_proof_index": group_spec["sub_proof_index"],
                        **group_spec["values"].get(attr),
                    }
                    for attr in req_attr["names"]
                }
            else:
                LOGGER.debug("Request attribute missing 'name' and 'names'")
                return PreVerifyResult.INCOMPLETE

            for (attr, spec) in pres_req_attr_spec.items():
                try:
                    primary_enco = pres["proof"]["proofs"][spec["sub_proof_index"]][
                        "primary_proof"
                    ]["eq_proof"]["revealed_attrs"][canon(attr)]
                except (KeyError, TypeError):
                    return PreVerifyResult.INCOMPLETE
                if primary_enco != spec["encoded"]:
                    LOGGER.debug("Encoded representation mismatch for '%s'", attr)
                    return PreVerifyResult.ENCODING_MISMATCH
                if primary_enco != encode(spec["raw"]):
                    LOGGER.debug("Encoded representation mismatch for '%s'", attr)
                    return PreVerifyResult.ENCODING_MISMATCH

        return PreVerifyResult.OK

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

        pv_result = self.pre_verify(presentation_request, presentation)
        if pv_result != PreVerifyResult.OK:
            LOGGER.error(
                f"Presentation on nonce={presentation_request['nonce']} "
                f"cannot be validated: {pv_result.value}"
            )
            return False

        verified = await indy.anoncreds.verifier_verify_proof(
            json.dumps(presentation_request),
            json.dumps(presentation),
            json.dumps(schemas),
            json.dumps(credential_definitions),
            json.dumps({}),  # no revocation
            json.dumps({}),
        )

        return verified
