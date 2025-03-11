"""V2.0 present-proof anoncreds presentation-exchange format handler."""

import json
import logging
from typing import Mapping, Optional, Tuple

from marshmallow import RAISE

from ......anoncreds.holder import AnonCredsHolder
from ......anoncreds.models.predicate import Predicate
from ......anoncreds.models.presentation_request import AnonCredsPresentationRequestSchema
from ......anoncreds.models.proof import AnonCredsProofSchema
from ......anoncreds.models.utils import get_requested_creds_from_proof_request_preview
from ......anoncreds.registry import AnonCredsRegistry
from ......anoncreds.util import generate_pr_nonce
from ......anoncreds.verifier import AnonCredsVerifier
from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.util import canon
from ....anoncreds.pres_exch_handler import AnonCredsPresExchHandler
from ...message_types import ATTACHMENT_FORMAT, PRES_20, PRES_20_PROPOSAL, PRES_20_REQUEST
from ...messages.pres import V20Pres
from ...messages.pres_format import V20PresFormat
from ...models.pres_exchange import V20PresExRecord
from ..handler import V20PresFormatHandler, V20PresFormatHandlerError

LOGGER = logging.getLogger(__name__)


class AnonCredsPresExchangeHandler(V20PresFormatHandler):
    """AnonCreds presentation format handler."""

    format = V20PresFormat.Format.ANONCREDS

    @classmethod
    def validate_fields(cls, message_type: str, attachment_data: Mapping):
        """Validate attachment data for a specific message type.

        Uses marshmallow schemas to validate if format specific attachment data
        is valid for the specified message type. Only does structural and type
        checks, does not validate if .e.g. the issuer value is valid.


        Args:
            message_type (str): The message type to validate the attachment data for.
                Should be one of the message types as defined in message_types.py
            attachment_data (Mapping): [description]
                The attachment data to validate

        Raises:
            Exception: When the data is not valid.

        """
        mapping = {
            PRES_20_REQUEST: AnonCredsPresentationRequestSchema,
            PRES_20_PROPOSAL: AnonCredsPresentationRequestSchema,
            PRES_20: AnonCredsProofSchema,
        }

        # Get schema class
        Schema = mapping[message_type]

        # Validate, throw if not valid
        Schema(unknown=RAISE).load(attachment_data)

    def get_format_identifier(self, message_type: str) -> str:
        """Get attachment format identifier for format and message combination.

        Args:
            message_type (str): Message type for which to return the format identifier

        Returns:
            str: Issue credential attachment format identifier

        """
        return ATTACHMENT_FORMAT[message_type][AnonCredsPresExchangeHandler.format.api]

    def get_format_data(
        self, message_type: str, data: dict
    ) -> Tuple[V20PresFormat, AttachDecorator]:
        """Get presentation format and attach objects for use in pres_ex messages."""
        return (
            V20PresFormat(
                attach_id=AnonCredsPresExchangeHandler.format.api,
                format_=self.get_format_identifier(message_type),
            ),
            AttachDecorator.data_base64(
                data,
                ident=AnonCredsPresExchangeHandler.format.api,
            ),
        )

    async def create_bound_request(
        self,
        pres_ex_record: V20PresExRecord,
        request_data: Optional[dict] = None,
    ) -> Tuple[V20PresFormat, AttachDecorator]:
        """Create a presentation request bound to a proposal.

        Args:
            pres_ex_record: Presentation exchange record for which
                to create presentation request
            request_data: Dict

        Returns:
            A tuple (updated presentation exchange record, presentation request message)

        """
        proof_request = pres_ex_record.pres_proposal.attachment(
            AnonCredsPresExchangeHandler.format
        )
        if request_data:
            proof_request["name"] = request_data.get("name", "proof-request")
            proof_request["version"] = request_data.get("version", "1.0")
            proof_request["nonce"] = (
                request_data.get("nonce") or await generate_pr_nonce()
            )
        else:
            proof_request["name"] = "proof-request"
            proof_request["version"] = "1.0"
            proof_request["nonce"] = await generate_pr_nonce()
        return self.get_format_data(PRES_20_REQUEST, proof_request)

    async def create_pres(
        self,
        pres_ex_record: V20PresExRecord,
        request_data: Optional[dict] = None,
    ) -> Tuple[V20PresFormat, AttachDecorator]:
        """Create a presentation."""
        requested_credentials = {}

        # This is used for the fallback to indy format
        from ..indy.handler import IndyPresExchangeHandler

        if not request_data:
            try:
                proof_request = pres_ex_record.pres_request
                # Fall back to indy format should be removed when indy format retired
                proof_request = proof_request.attachment(
                    AnonCredsPresExchangeHandler.format
                ) or proof_request.attachment(IndyPresExchangeHandler.format)
                requested_credentials = (
                    await get_requested_creds_from_proof_request_preview(
                        proof_request,
                        holder=AnonCredsHolder(self._profile),
                    )
                )
            except ValueError as err:
                LOGGER.warning(f"{err}")
                raise V20PresFormatHandlerError(f"No matching credentials found: {err}")
        else:
            # Fall back to indy format should be removed when indy format retired
            if (
                AnonCredsPresExchangeHandler.format.api in request_data
                or IndyPresExchangeHandler.format.api in request_data
            ):
                spec = request_data.get(
                    AnonCredsPresExchangeHandler.format.api
                ) or request_data.get(IndyPresExchangeHandler.format.api)
                requested_credentials = {
                    "self_attested_attributes": spec["self_attested_attributes"],
                    "requested_attributes": spec["requested_attributes"],
                    "requested_predicates": spec["requested_predicates"],
                }
        handler = AnonCredsPresExchHandler(self._profile)
        presentation_proof = await handler.return_presentation(
            pres_ex_record=pres_ex_record,
            requested_credentials=requested_credentials,
        )

        # This is used for the fallback to indy format. Should be removed when indy
        # format retired
        if request_data.get("indy"):
            return IndyPresExchangeHandler(self.profile).get_format_data(
                PRES_20, presentation_proof
            )
        return self.get_format_data(PRES_20, presentation_proof)

    async def receive_pres(self, message: V20Pres, pres_ex_record: V20PresExRecord):
        """Receive a presentation and check for presented values vs. proposal request."""

        async def _check_proof_vs_proposal():
            """Check for bait and switch in presented values vs. proposal request."""
            from ..indy.handler import IndyPresExchangeHandler

            # Fall back to indy format should be removed when indy format retired
            proof_req = pres_ex_record.pres_request.attachment(
                AnonCredsPresExchangeHandler.format
            ) or pres_ex_record.pres_request.attachment(IndyPresExchangeHandler.format)

            # revealed attrs
            for reft, attr_spec in proof["requested_proof"]["revealed_attrs"].items():
                proof_req_attr_spec = proof_req["requested_attributes"].get(reft)
                if not proof_req_attr_spec:
                    raise V20PresFormatHandlerError(
                        f"Presentation referent {reft} not in proposal request"
                    )
                req_restrictions = proof_req_attr_spec.get("restrictions", {})

                name = proof_req_attr_spec["name"]
                proof_value = attr_spec["raw"]
                sub_proof_index = attr_spec["sub_proof_index"]
                schema_id = proof["identifiers"][sub_proof_index]["schema_id"]
                cred_def_id = proof["identifiers"][sub_proof_index]["cred_def_id"]
                registry = self.profile.inject(AnonCredsRegistry)
                schema = await registry.get_schema(self.profile, schema_id)
                cred_def = await registry.get_credential_definition(
                    self.profile, cred_def_id
                )
                criteria = {
                    "schema_id": schema_id,
                    "schema_issuer_did": schema.schema_value.issuer_id,
                    "schema_name": schema.schema_value.name,
                    "schema_version": schema.schema_value.version,
                    "cred_def_id": cred_def_id,
                    "issuer_did": cred_def.credential_definition.issuer_id,
                    f"attr::{name}::value": proof_value,
                }

                if (
                    not any(r.items() <= criteria.items() for r in req_restrictions)
                    and len(req_restrictions) != 0
                ):
                    raise V20PresFormatHandlerError(
                        f"Presented attribute {reft} does not satisfy proof request "
                        f"restrictions {req_restrictions}"
                    )

            # revealed attr groups
            for reft, attr_spec in (
                proof["requested_proof"].get("revealed_attr_groups", {}).items()
            ):
                proof_req_attr_spec = proof_req["requested_attributes"].get(reft)
                if not proof_req_attr_spec:
                    raise V20PresFormatHandlerError(
                        f"Presentation referent {reft} not in proposal request"
                    )
                req_restrictions = proof_req_attr_spec.get("restrictions", {})
                proof_values = {
                    name: values["raw"] for name, values in attr_spec["values"].items()
                }
                sub_proof_index = attr_spec["sub_proof_index"]
                schema_id = proof["identifiers"][sub_proof_index]["schema_id"]
                cred_def_id = proof["identifiers"][sub_proof_index]["cred_def_id"]
                registry = self.profile.inject(AnonCredsRegistry)
                schema = await registry.get_schema(self.profile, schema_id)
                cred_def = await registry.get_credential_definition(
                    self.profile, cred_def_id
                )
                criteria = {
                    "schema_id": schema_id,
                    "schema_issuer_did": schema.schema_value.issuer_id,
                    "schema_name": schema.schema_value.name,
                    "schema_version": schema.schema_value.version,
                    "cred_def_id": cred_def_id,
                    "issuer_did": cred_def.credential_definition.issuer_id,
                    **{
                        f"attr::{name}::value": value
                        for name, value in proof_values.items()
                    },
                }

                if (
                    not any(r.items() <= criteria.items() for r in req_restrictions)
                    and len(req_restrictions) != 0
                ):
                    raise V20PresFormatHandlerError(
                        f"Presented attr group {reft} does not satisfy proof request "
                        f"restrictions {req_restrictions}"
                    )

            # predicate bounds
            for reft, pred_spec in proof["requested_proof"]["predicates"].items():
                proof_req_pred_spec = proof_req["requested_predicates"].get(reft)
                if not proof_req_pred_spec:
                    raise V20PresFormatHandlerError(
                        f"Presentation referent {reft} not in proposal request"
                    )
                req_name = proof_req_pred_spec["name"]
                req_pred = Predicate.get(proof_req_pred_spec["p_type"])
                req_value = proof_req_pred_spec["p_value"]
                req_restrictions = proof_req_pred_spec.get("restrictions", {})
                for req_restriction in req_restrictions:
                    for k in list(req_restriction):  # cannot modify en passant
                        if k.startswith("attr::"):
                            # let anoncreds-sdk reject mismatch here
                            req_restriction.pop(k)
                sub_proof_index = pred_spec["sub_proof_index"]
                for ge_proof in proof["proof"]["proofs"][sub_proof_index][
                    "primary_proof"
                ]["ge_proofs"]:
                    proof_pred_spec = ge_proof["predicate"]
                    if proof_pred_spec["attr_name"] != canon(req_name):
                        continue
                    if not (
                        Predicate.get(proof_pred_spec["p_type"]) is req_pred
                        and proof_pred_spec["value"] == req_value
                    ):
                        raise V20PresFormatHandlerError(
                            f"Presentation predicate on {req_name} "
                            "mismatches proposal request"
                        )
                    break
                else:
                    raise V20PresFormatHandlerError(
                        f"Proposed request predicate on {req_name} not in presentation"
                    )

                schema_id = proof["identifiers"][sub_proof_index]["schema_id"]
                cred_def_id = proof["identifiers"][sub_proof_index]["cred_def_id"]
                registry = self.profile.inject(AnonCredsRegistry)
                schema = await registry.get_schema(self.profile, schema_id)
                cred_def = await registry.get_credential_definition(
                    self.profile, cred_def_id
                )
                criteria = {
                    "schema_id": schema_id,
                    "schema_issuer_did": schema.schema_value.issuer_id,
                    "schema_name": schema.schema_value.name,
                    "schema_version": schema.schema_value.version,
                    "cred_def_id": cred_def_id,
                    "issuer_did": cred_def.credential_definition.issuer_id,
                }

                if (
                    not any(r.items() <= criteria.items() for r in req_restrictions)
                    and len(req_restrictions) != 0
                ):
                    raise V20PresFormatHandlerError(
                        f"Presented predicate {reft} does not satisfy proof request "
                        f"restrictions {req_restrictions}"
                    )

        proof = message.attachment(AnonCredsPresExchangeHandler.format)
        await _check_proof_vs_proposal()

    async def verify_pres(self, pres_ex_record: V20PresExRecord) -> V20PresExRecord:
        """Verify a presentation.

        Args:
            pres_ex_record: presentation exchange record
                with presentation request and presentation to verify

        Returns:
            presentation exchange record, updated

        """
        pres_request_msg = pres_ex_record.pres_request
        proof_request = pres_request_msg.attachment(AnonCredsPresExchangeHandler.format)
        proof = pres_ex_record.pres.attachment(AnonCredsPresExchangeHandler.format)
        verifier = AnonCredsVerifier(self._profile)

        (
            schemas,
            cred_defs,
            rev_reg_defs,
            rev_lists,
        ) = await verifier.process_pres_identifiers(proof["identifiers"])

        verifier = AnonCredsVerifier(self._profile)

        (verified, verified_msgs) = await verifier.verify_presentation(
            proof_request,
            proof,
            schemas,
            cred_defs,
            rev_reg_defs,
            rev_lists,
        )
        pres_ex_record.verified = json.dumps(verified)
        pres_ex_record.verified_msgs = list(set(verified_msgs))
        return pres_ex_record
