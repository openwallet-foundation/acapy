"""V2.0 issue-credential linked data proof credential format handler."""

import logging
from typing import Mapping

from marshmallow import EXCLUDE, INCLUDE
from pyld import jsonld
from pyld.jsonld import JsonLdProcessor

from ......messaging.decorators.attach_decorator import AttachDecorator
from ......storage.vc_holder.base import VCHolder
from ......storage.vc_holder.vc_record import VCRecord
from ......vc.ld_proofs import DocumentLoader
from ......vc.ld_proofs.check import get_properties_without_context
from ......vc.ld_proofs.error import LinkedDataProofException
from ......vc.vc_ld import VerifiableCredential, VerifiableCredentialSchema
from ......vc.vc_ld.manager import VcLdpManager, VcLdpManagerError
from ......vc.vc_ld.models.options import LDProofVCOptions
from ...message_types import (
    ATTACHMENT_FORMAT,
    CRED_20_ISSUE,
    CRED_20_OFFER,
    CRED_20_PROPOSAL,
    CRED_20_REQUEST,
)
from ...messages.cred_format import V20CredFormat
from ...messages.cred_issue import V20CredIssue
from ...messages.cred_offer import V20CredOffer
from ...messages.cred_proposal import V20CredProposal
from ...messages.cred_request import V20CredRequest
from ...models.cred_ex_record import V20CredExRecord
from ...models.detail.ld_proof import V20CredExRecordLDProof
from ..handler import CredFormatAttachment, V20CredFormatError, V20CredFormatHandler
from .models.cred_detail import LDProofVCDetail, LDProofVCDetailSchema

LOGGER = logging.getLogger(__name__)


class LDProofCredFormatHandler(V20CredFormatHandler):
    """Linked data proof credential format handler."""

    format = V20CredFormat.Format.LD_PROOF

    @classmethod
    def validate_fields(cls, message_type: str, attachment_data: Mapping) -> None:
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
            CRED_20_PROPOSAL: LDProofVCDetailSchema,
            CRED_20_OFFER: LDProofVCDetailSchema,
            CRED_20_REQUEST: LDProofVCDetailSchema,
            CRED_20_ISSUE: VerifiableCredentialSchema,
        }

        # Get schema class
        Schema = mapping[message_type]

        # Validate, throw if not valid
        Schema(unknown=EXCLUDE).load(attachment_data)

    async def get_detail_record(self, cred_ex_id: str) -> V20CredExRecordLDProof:
        """Retrieve credential exchange detail record by cred_ex_id."""

        async with self.profile.session() as session:
            records = await LDProofCredFormatHandler.format.detail.query_by_cred_ex_id(
                session, cred_ex_id
            )

        if len(records) > 1:
            LOGGER.warning(
                "Cred ex id %s has %d %s detail records: should be 1",
                cred_ex_id,
                len(records),
                LDProofCredFormatHandler.format.api,
            )
        return records[0] if records else None

    def get_format_identifier(self, message_type: str) -> str:
        """Get attachment format identifier for format and message combination.

        Args:
            message_type (str): Message type for which to return the format identifier

        Returns:
            str: Issue credential attachment format identifier

        """
        return ATTACHMENT_FORMAT[message_type][LDProofCredFormatHandler.format.api]

    def get_format_data(self, message_type: str, data: dict) -> CredFormatAttachment:
        """Get credential format and attachment objects for use in cred ex messages.

        Returns a tuple of both credential format and attachment decorator for use
        in credential exchange messages. It looks up the correct format identifier and
        encodes the data as a base64 attachment.

        Args:
            message_type (str): The message type for which to return the cred format.
                Should be one of the message types defined in the message types file
            data (dict): The data to include in the attach decorator

        Returns:
            CredFormatAttachment: Credential format and attachment data objects

        """
        return (
            V20CredFormat(
                attach_id=LDProofCredFormatHandler.format.api,
                format_=self.get_format_identifier(message_type),
            ),
            AttachDecorator.data_base64(
                data, ident=LDProofCredFormatHandler.format.api
            ),
        )

    async def create_proposal(
        self, cred_ex_record: V20CredExRecord, proposal_data: Mapping
    ) -> CredFormatAttachment:
        """Create linked data proof credential proposal."""
        manager = VcLdpManager(self.profile)
        detail = LDProofVCDetail.deserialize(proposal_data)
        assert detail.options and isinstance(detail.options, LDProofVCOptions)
        assert detail.credential and isinstance(detail.credential, VerifiableCredential)
        try:
            detail.credential = await manager.prepare_credential(
                detail.credential, detail.options
            )
        except VcLdpManagerError as err:
            raise V20CredFormatError("Failed to prepare credential") from err

        return self.get_format_data(CRED_20_PROPOSAL, detail.serialize())

    async def receive_proposal(
        self, cred_ex_record: V20CredExRecord, cred_proposal_message: V20CredProposal
    ) -> None:
        """Receive linked data proof credential proposal."""

    async def create_offer(
        self, cred_proposal_message: V20CredProposal
    ) -> CredFormatAttachment:
        """Create linked data proof credential offer."""
        if not cred_proposal_message:
            raise V20CredFormatError(
                "Cannot create linked data proof offer without proposal data"
            )

        # Parse offer data which is either a proposal or an offer.
        # Data is stored in proposal if we received a proposal
        # but also when we create an offer (manager does some weird stuff)
        offer_data = cred_proposal_message.attachment(LDProofCredFormatHandler.format)
        detail = LDProofVCDetail.deserialize(offer_data)
        manager = VcLdpManager(self.profile)
        assert detail.options and isinstance(detail.options, LDProofVCOptions)
        assert detail.credential and isinstance(detail.credential, VerifiableCredential)
        try:
            detail.credential = await manager.prepare_credential(
                detail.credential, detail.options
            )
        except VcLdpManagerError as err:
            raise V20CredFormatError("Failed to prepare credential") from err

        document_loader = self.profile.inject(DocumentLoader)
        missing_properties = get_properties_without_context(
            detail.credential.serialize(), document_loader
        )

        if len(missing_properties) > 0:
            raise LinkedDataProofException(
                f"{len(missing_properties)} attributes dropped. "
                f"Provide definitions in context to correct. {missing_properties}"
            )

        # Make sure we can issue with the did and proof type
        try:
            await manager.assert_can_issue_with_id_and_proof_type(
                detail.credential.issuer_id, detail.options.proof_type
            )
        except VcLdpManagerError as err:
            raise V20CredFormatError(
                "Checking whether issuance is possible failed"
            ) from err

        return self.get_format_data(CRED_20_OFFER, detail.serialize())

    async def receive_offer(
        self, cred_ex_record: V20CredExRecord, cred_offer_message: V20CredOffer
    ) -> None:
        """Receive linked data proof credential offer."""

    async def create_request(
        self, cred_ex_record: V20CredExRecord, request_data: Mapping = None
    ) -> CredFormatAttachment:
        """Create linked data proof credential request."""
        holder_did = request_data.get("holder_did") if request_data else None

        if cred_ex_record.cred_offer:
            request_data = cred_ex_record.cred_offer.attachment(
                LDProofCredFormatHandler.format
            )
        # API data is stored in proposal (when starting from request)
        # It is a bit of a strange flow IMO.
        elif cred_ex_record.cred_proposal:
            request_data = cred_ex_record.cred_proposal.attachment(
                LDProofCredFormatHandler.format
            )
        else:
            raise V20CredFormatError(
                "Cannot create linked data proof request without offer or input data"
            )

        detail = LDProofVCDetail.deserialize(request_data)
        manager = VcLdpManager(self.profile)
        assert detail.options and isinstance(detail.options, LDProofVCOptions)
        assert detail.credential and isinstance(detail.credential, VerifiableCredential)
        try:
            detail.credential = await manager.prepare_credential(
                detail.credential, detail.options, holder_did=holder_did
            )
        except VcLdpManagerError as err:
            raise V20CredFormatError("Failed to prepare credential") from err

        return self.get_format_data(CRED_20_REQUEST, detail.serialize())

    def can_receive_request_without_offer(
        self,
    ) -> bool:
        """Can this handler receive credential request without an offer?"""
        return True

    async def receive_request(
        self, cred_ex_record: V20CredExRecord, cred_request_message: V20CredRequest
    ) -> None:
        """Receive linked data proof request."""
        # Check that request hasn't substantially changed from offer, if offer sent
        if cred_ex_record.cred_offer:
            offer_detail_dict = cred_ex_record.cred_offer.attachment(
                LDProofCredFormatHandler.format
            )
            req_detail_dict = cred_request_message.attachment(
                LDProofCredFormatHandler.format
            )

            # If credentialSubject.id in offer, it should be the same in request
            offer_id = (
                offer_detail_dict["credential"].get("credentialSubject", {}).get("id")
            )
            request_id = (
                req_detail_dict["credential"].get("credentialSubject", {}).get("id")
            )
            if offer_id and offer_id != request_id:
                raise V20CredFormatError(
                    "Request credentialSubject.id must match offer credentialSubject.id"
                )

            # Nothing else should be different about the request
            if request_id:
                offer_detail_dict["credential"].setdefault("credentialSubject", {})[
                    "id"
                ] = request_id
            if offer_detail_dict != req_detail_dict:
                raise V20CredFormatError("Request must match offer if offer is sent")

    async def issue_credential(
        self,
        cred_ex_record: V20CredExRecord,
        retries: int = 5,
    ) -> CredFormatAttachment:
        """Issue linked data proof credential."""
        if not cred_ex_record.cred_request:
            raise V20CredFormatError(
                "Cannot issue credential without credential request"
            )

        detail_dict = cred_ex_record.cred_request.attachment(
            LDProofCredFormatHandler.format
        )
        detail = LDProofVCDetail.deserialize(detail_dict)
        manager = VcLdpManager(self.profile)
        assert detail.options and isinstance(detail.options, LDProofVCOptions)
        assert detail.credential and isinstance(detail.credential, VerifiableCredential)
        try:
            vc = await manager.issue(detail.credential, detail.options)
        except VcLdpManagerError as err:
            raise V20CredFormatError("Failed to issue credential") from err

        return self.get_format_data(CRED_20_ISSUE, vc.serialize())

    async def receive_credential(
        self, cred_ex_record: V20CredExRecord, cred_issue_message: V20CredIssue
    ) -> None:
        """Receive linked data proof credential."""
        cred_dict = cred_issue_message.attachment(LDProofCredFormatHandler.format)
        detail_dict = cred_ex_record.cred_request.attachment(
            LDProofCredFormatHandler.format
        )

        vc = VerifiableCredential.deserialize(cred_dict, unknown=INCLUDE)
        detail = LDProofVCDetail.deserialize(detail_dict)

        # Remove values from cred that are not part of detail
        cred_dict.pop("proof")
        credential_status = cred_dict.get("credentialStatus", None)
        detail_status = detail.options.credential_status

        if cred_dict != detail_dict["credential"]:
            raise V20CredFormatError(
                f"Received credential for cred_ex_id {cred_ex_record.cred_ex_id} does not"
                " match requested credential"
            )

        # both credential and detail contain status. Check for equality
        if credential_status and detail_status:
            if credential_status.get("type") != detail_status.get("type"):
                raise V20CredFormatError(
                    "Received credential status type does not match credential request"
                )
        # Either credential or detail contains status. Throw error
        elif (credential_status and not detail_status) or (
            not credential_status and detail_status
        ):
            raise V20CredFormatError(
                "Received credential status contains credential status"
                " that does not match credential request"
            )

        # TODO: if created wasn't present in the detail options, should we verify
        # it is ~now (e.g. some time in the past + future)?
        # Check if created property matches
        if detail.options.created and vc.proof.created != detail.options.created:
            raise V20CredFormatError(
                "Received credential proof.created does not"
                " match options.created from credential request"
            )

        # Check challenge
        if vc.proof.challenge != detail.options.challenge:
            raise V20CredFormatError(
                "Received credential proof.challenge does not"
                " match options.challenge from credential request"
            )

        # Check domain
        if vc.proof.domain != detail.options.domain:
            raise V20CredFormatError(
                "Received credential proof.domain does not"
                " match options.domain from credential request"
            )

        # Check if proof type matches
        if vc.proof.type != detail.options.proof_type:
            raise V20CredFormatError(
                "Received credential proof.type does not"
                " match options.proofType from credential request"
            )

    async def store_credential(
        self, cred_ex_record: V20CredExRecord, cred_id: str = None
    ) -> None:
        """Store linked data proof credential."""
        # Get attachment data
        cred_dict: dict = cred_ex_record.cred_issue.attachment(
            LDProofCredFormatHandler.format
        )

        # Deserialize objects
        credential = VerifiableCredential.deserialize(cred_dict, unknown=INCLUDE)

        # Get signature suite, proof purpose and document loader
        manager = VcLdpManager(self.profile)
        try:
            result = await manager.verify_credential(credential)
        except VcLdpManagerError as err:
            raise V20CredFormatError("Failed to verify credential") from err

        if not result.verified:
            raise V20CredFormatError(f"Received invalid credential: {result}")

        # Saving expanded type as a cred_tag
        document_loader = self.profile.inject(DocumentLoader)
        expanded = jsonld.expand(cred_dict, options={"documentLoader": document_loader})
        types = JsonLdProcessor.get_values(
            expanded[0],
            "@type",
        )

        # create VC record for storage
        vc_record = VCRecord(
            contexts=credential.context_urls,
            expanded_types=types,
            issuer_id=credential.issuer_id,
            subject_ids=credential.credential_subject_ids,
            schema_ids=[],  # Schemas not supported yet
            proof_types=[credential.proof.type],
            cred_value=credential.serialize(),
            given_id=credential.id,
            record_id=cred_id,
            cred_tags=None,  # Tags should be derived from credential values
        )

        # Create detail record with cred_id_stored
        detail_record = V20CredExRecordLDProof(
            cred_ex_id=cred_ex_record.cred_ex_id, cred_id_stored=vc_record.record_id
        )

        # save credential and detail record
        async with self.profile.session() as session:
            vc_holder = session.inject(VCHolder)

            await vc_holder.store_credential(vc_record)
            # Store detail record, emit event
            await detail_record.save(
                session, reason="store credential v2.0", event=True
            )
