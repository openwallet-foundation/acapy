"""Indy verifier implementation."""

import json
import logging

import indy.anoncreds

from ..messaging.util import canon, encode
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

    @staticmethod
    def check_encoding(pres_req: dict, pres: dict) -> bool:
        """
        Check for tampering in presentation.

        Visit encoded attribute values against raw, and predicate bounds,
        in presentation, cross-reference against presentation request.

        Args:
            pres_req: presentation request
            pres: corresponding presentation

        Returns:
            True for OK, False for tamper evidence

        """
        for (uuid, req_pred) in pres_req["requested_predicates"].items():
            canon_attr = canon(req_pred["name"])
            for ge_proof in pres["proof"]["proofs"][
                pres["requested_proof"]["predicates"][
                    uuid
                ]["sub_proof_index"]
            ]["primary_proof"]["ge_proofs"]:
                pred = ge_proof["predicate"]
                if pred["attr_name"] == canon_attr:
                    if pred["value"] != req_pred["p_value"]:
                        return False
                    break
            else:
                return False  # missing predicate in proof

        for (uuid, req_attr) in pres_req["requested_attributes"].items():
            if "name" in req_attr:
                pres_req_attr_spec = {
                    req_attr["name"]: pres["requested_proof"]["revealed_attrs"][uuid]
                }
            else:
                group_spec = pres["requested_proof"].get(
                    "revealed_attr_groups",
                    {}
                ).get(uuid)
                if group_spec is None:
                    return False
                pres_req_attr_spec = {
                    attr: {
                        "sub_proof_index": group_spec["sub_proof_index"],
                        **pres["requested_proof"]["revealed_attr_groups"][
                            uuid
                        ]["values"][attr]
                    } for attr in req_attr["names"]
                }

            for (attr, spec) in pres_req_attr_spec.items():
                primary_enco = pres["proof"]["proofs"][
                    spec["sub_proof_index"]
                ]["primary_proof"]["eq_proof"]["revealed_attrs"].get(canon(attr))
                if primary_enco != spec["encoded"]:
                    return False
                if primary_enco != encode(spec["raw"]):
                    return False

            return True

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

        if not IndyVerifier.check_encoding(presentation_request, presentation):
            self.logger.error(
                f"Presentation on nonce={presentation_request['nonce']} "
                "demonstrates tampering with raw values"
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
