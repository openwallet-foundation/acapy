"""V2.0 issue-credential protocol manager."""

import logging

from typing import Mapping, Optional, Tuple, Sequence
from uuid import uuid4

from ....connections.models.conn_record import ConnRecord
from ....core.oob_processor import OobRecord
from ....core.error import BaseError
from ....core.profile import Profile
from ....messaging.responder import BaseResponder
from ....storage.error import StorageError, StorageNotFoundError

from .messages.cred_ack import V20CredAck
from .messages.cred_format import V20CredFormat
from .messages.cred_issue import V20CredIssue
from .messages.cred_offer import V20CredOffer
from .messages.cred_problem_report import V20CredProblemReport, ProblemReportReason
from .messages.cred_proposal import V20CredProposal
from .messages.cred_request import V20CredRequest
from .messages.inner.cred_preview import V20CredPreview
from .models.cred_ex_record import V20CredExRecord

LOGGER = logging.getLogger(__name__)


class V20CredManagerError(BaseError):
    """Credential manager error under issue-credential protocol v2.0."""


class V20CredManager:
    """Class for managing credentials."""

    def __init__(self, profile: Profile):
        """
        Initialize a V20CredManager.

        Args:
            profile: The profile instance for this credential manager
        """
        self._profile = profile

    @property
    def profile(self) -> Profile:
        """
        Accessor for the current profile instance.

        Returns:
            The profile instance for this credential manager

        """
        return self._profile

    async def prepare_send(
        self,
        connection_id: str,
        cred_proposal: V20CredProposal,
        auto_remove: bool = None,
    ) -> Tuple[V20CredExRecord, V20CredOffer]:
        """
        Set up a new credential exchange record for an automated send.

        Args:
            connection_id: connection for which to create offer
            cred_proposal: credential proposal with preview
            auto_remove: flag to remove the record automatically on completion

        Returns:
            A tuple of the new credential exchange record and credential offer message

        """
        if auto_remove is None:
            auto_remove = not self._profile.settings.get("preserve_exchange_records")
        cred_ex_record = V20CredExRecord(
            connection_id=connection_id,
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            cred_proposal=cred_proposal,
            auto_issue=True,
            auto_remove=auto_remove,
            trace=(cred_proposal._trace is not None),
        )
        (cred_ex_record, cred_offer) = await self.create_offer(
            cred_ex_record=cred_ex_record,
            counter_proposal=None,
            comment="create automated v2.0 credential exchange record",
        )
        return (cred_ex_record, cred_offer)

    async def create_proposal(
        self,
        connection_id: str,
        *,
        auto_remove: bool = None,
        comment: str = None,
        cred_preview: V20CredPreview,
        fmt2filter: Mapping[V20CredFormat.Format, Mapping[str, str]],
        trace: bool = False,
    ) -> V20CredExRecord:
        """
        Create a credential proposal.

        Args:
            connection_id: connection for which to create proposal
            auto_remove: whether to remove record automatically on completion
            comment: optional human-readable comment to include in proposal
            cred_preview: credential preview to use to create credential proposal
            fmt2filter: mapping between format and filter
            trace: whether to trace the operation

        Returns:
            Resulting credential exchange record including credential proposal

        """

        if auto_remove is None:
            auto_remove = not self._profile.settings.get("preserve_exchange_records")
        cred_ex_record = V20CredExRecord(
            connection_id=connection_id,
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_HOLDER,
            state=V20CredExRecord.STATE_PROPOSAL_SENT,
            auto_remove=auto_remove,
            trace=trace,
        )

        # Format specific create_proposal handler
        formats = [
            await fmt.handler(self._profile).create_proposal(cred_ex_record, filter)
            for (fmt, filter) in fmt2filter.items()
        ]

        cred_proposal_message = V20CredProposal(
            comment=comment,
            credential_preview=cred_preview,
            formats=[format for (format, _) in formats],
            filters_attach=[attach for (_, attach) in formats],
        )

        cred_ex_record.thread_id = cred_proposal_message._thread_id
        cred_ex_record.cred_proposal = cred_proposal_message

        cred_proposal_message.assign_trace_decorator(self._profile.settings, trace)

        async with self._profile.session() as session:
            await cred_ex_record.save(
                session,
                reason="create v2.0 credential proposal",
            )
        return cred_ex_record

    async def receive_proposal(
        self,
        cred_proposal_message: V20CredProposal,
        connection_id: str,
    ) -> V20CredExRecord:
        """
        Receive a credential proposal.

        Returns:
            The resulting credential exchange record, created

        """
        # at this point, cred def and schema still open to potential negotiation
        cred_ex_record = V20CredExRecord(
            connection_id=connection_id,
            thread_id=cred_proposal_message._thread_id,
            initiator=V20CredExRecord.INITIATOR_EXTERNAL,
            role=V20CredExRecord.ROLE_ISSUER,
            auto_offer=self._profile.settings.get(
                "debug.auto_respond_credential_proposal"
            ),
            auto_issue=self._profile.settings.get(
                "debug.auto_respond_credential_request"
            ),
            auto_remove=not self._profile.settings.get("preserve_exchange_records"),
            trace=(cred_proposal_message._trace is not None),
        )

        # Format specific receive_proposal handlers
        for format in cred_proposal_message.formats:
            await V20CredFormat.Format.get(format.format).handler(
                self.profile
            ).receive_proposal(cred_ex_record, cred_proposal_message)

        cred_ex_record.cred_proposal = cred_proposal_message
        cred_ex_record.state = V20CredExRecord.STATE_PROPOSAL_RECEIVED

        async with self._profile.session() as session:
            await cred_ex_record.save(
                session,
                reason="receive v2.0 credential proposal",
            )

        return cred_ex_record

    async def create_offer(
        self,
        cred_ex_record: V20CredExRecord,
        counter_proposal: V20CredProposal = None,
        replacement_id: str = None,
        comment: str = None,
        multiple_available: int = 1,
    ) -> Tuple[V20CredExRecord, V20CredOffer]:
        """
        Create credential offer, update credential exchange record.

        Args:
            cred_ex_record: credential exchange record for which to create offer
            replacement_id: identifier to help coordinate credential replacement
            comment: optional human-readable comment to set in offer message
            multiple_available: Count of verifiable credentials of the indicated
                type available for issuance.
        Returns:
            A tuple (credential exchange record, credential offer message)

        """

        cred_proposal_message = (
            counter_proposal if counter_proposal else cred_ex_record.cred_proposal
        )
        cred_proposal_message.assign_trace_decorator(
            self._profile.settings, cred_ex_record.trace
        )

        formats = []
        # Format specific create_offer handler
        for format in cred_proposal_message.formats:
            cred_format = V20CredFormat.Format.get(format.format)
            if cred_format:
                attach_id = (
                    format.attach_id if format.attach_id != cred_format.api else None
                )
                formats.append(
                    await cred_format.handler(self.profile).create_offer(
                        cred_proposal_message=cred_proposal_message, attach_id=attach_id
                    )
                )

        if len(formats) == 0:
            raise V20CredManagerError(
                "Unable to create credential offer. No supported formats"
            )
        elif len(formats) >= 2:
            if not multiple_available or multiple_available <= 1:
                raise V20CredManagerError(
                    "Multiple formats included but multiple_available"
                    f" is set as {str(multiple_available)}"
                )
            cred_ex_record.multiple_credentials = True
        if multiple_available > 1:
            cred_ex_record.multiple_credentials = True

        cred_offer_message = V20CredOffer(
            replacement_id=replacement_id,
            comment=comment,
            credential_preview=cred_proposal_message.credential_preview,
            formats=[format for (format, _) in formats],
            offers_attach=[attach for (_, attach) in formats],
            multiple_available=multiple_available,
        )

        cred_offer_message._thread = {"thid": cred_ex_record.thread_id}
        cred_offer_message.assign_trace_decorator(
            self._profile.settings, cred_ex_record.trace
        )

        cred_ex_record.thread_id = cred_offer_message._thread_id
        cred_ex_record.state = V20CredExRecord.STATE_OFFER_SENT
        cred_ex_record.cred_proposal = (  # any counter replaces original
            cred_proposal_message
        )
        cred_ex_record.cred_offer = cred_offer_message

        async with self._profile.session() as session:
            await cred_ex_record.save(session, reason="create v2.0 credential offer")

        return (cred_ex_record, cred_offer_message)

    async def receive_offer(
        self,
        cred_offer_message: V20CredOffer,
        connection_id: Optional[str],
    ) -> V20CredExRecord:
        """
        Receive a credential offer.

        Args:
            cred_offer_message: credential offer message
            connection_id: connection identifier

        Returns:
            The credential exchange record, updated

        """

        # Get credential exchange record (holder sent proposal first)
        # or create it (issuer sent offer first)
        try:
            async with self._profile.session() as session:
                cred_ex_record = await V20CredExRecord.retrieve_by_conn_and_thread(
                    session,
                    connection_id,
                    cred_offer_message._thread_id,
                    role=V20CredExRecord.ROLE_HOLDER,
                )
        except StorageNotFoundError:  # issuer sent this offer free of any proposal
            cred_ex_record = V20CredExRecord(
                connection_id=connection_id,
                thread_id=cred_offer_message._thread_id,
                initiator=V20CredExRecord.INITIATOR_EXTERNAL,
                role=V20CredExRecord.ROLE_HOLDER,
                auto_remove=not self._profile.settings.get("preserve_exchange_records"),
                trace=(cred_offer_message._trace is not None),
            )
        handled_formats = []
        # Format specific receive_offer handler
        for format in cred_offer_message.formats:
            cred_format = V20CredFormat.Format.get(format.format)

            if cred_format:
                await cred_format.handler(self.profile).receive_offer(
                    cred_ex_record, cred_offer_message
                )
                handled_formats.append(cred_format)

        if len(handled_formats) == 0:
            raise V20CredManagerError("No supported credential formats received.")
        elif len(handled_formats) >= 2:
            cred_ex_record.multiple_credentials = True

        cred_ex_record.cred_offer = cred_offer_message
        cred_ex_record.state = V20CredExRecord.STATE_OFFER_RECEIVED

        async with self._profile.session() as session:
            await cred_ex_record.save(session, reason="receive v2.0 credential offer")

        return cred_ex_record

    async def create_request(
        self,
        cred_ex_record: V20CredExRecord,
        holder_did: str,
        exclude_attach_ids: Sequence[str] = [],
        comment: str = None,
        multiple_credential_flow: bool = False,
    ) -> Tuple[V20CredExRecord, V20CredRequest]:
        """
        Create a credential request.

        Args:
            cred_ex_record: credential exchange record for which to create request
            holder_did: holder DID
            comment: optional human-readable comment to set in request message
            multiple_credential_flow: Flag to indicate if this is part of
                multiple credential issuance.
        Returns:
            A tuple (credential exchange record, credential request message)

        """
        cred_request_exists = False
        if cred_ex_record.cred_request:
            if multiple_credential_flow:
                cred_request_exists = True
            else:
                raise V20CredManagerError(
                    "create_request() called multiple times for "
                    f"v2.0 credential exchange {cred_ex_record.cred_ex_id}"
                )

        # react to credential offer, use offer formats
        if cred_ex_record.state:
            if cred_ex_record.state != V20CredExRecord.STATE_OFFER_RECEIVED:
                raise V20CredManagerError(
                    f"Credential exchange {cred_ex_record.cred_ex_id} "
                    f"in {cred_ex_record.state} state "
                    f"(must be {V20CredExRecord.STATE_OFFER_RECEIVED})"
                )

            cred_offer = cred_ex_record.cred_offer

            input_formats = cred_offer.formats
        # start with request (not allowed for indy -> checked in indy format handler)
        # use proposal formats
        else:
            cred_proposal = cred_ex_record.cred_proposal
            input_formats = cred_proposal.formats

        if cred_ex_record.multiple_issuance_state:
            if (
                cred_ex_record.multiple_issuance_state
                != V20CredExRecord.STATE_MULTIPLE_ISSUANCE_COMPLETE
                or cred_ex_record.multiple_issuance_state
                != V20CredExRecord.STATE_MULTIPLE_ISSUANCE_ABANDONED
            ):
                raise V20CredManagerError(
                    f"Credential exchange {cred_ex_record.cred_ex_id} "
                    f"in {cred_ex_record.multiple_issuance_state} "
                    "multiple_issuance_state"
                )

        request_formats = []
        # Format specific create_request handler
        for format in input_formats:
            cred_format = V20CredFormat.Format.get(format.format)

            if cred_format:
                attach_id = (
                    format.attach_id if format.attach_id != cred_format.api else None
                )
                if not attach_id and cred_request_exists:
                    attach_id = f"{attach_id}-{str(uuid4())}"
                if attach_id in exclude_attach_ids:
                    continue
                request_formats.append(
                    await cred_format.handler(self.profile).create_request(
                        cred_ex_record=cred_ex_record,
                        request_data={"holder_did": holder_did},
                        attach_id=attach_id,
                    )
                )

        if len(request_formats) == 0:
            raise V20CredManagerError(
                "Unable to create credential request. No supported formats"
            )
        elif len(request_formats) >= 2:
            cred_ex_record.multiple_credentials = True
            cred_ex_record.multiple_issuance_state = (
                V20CredExRecord.STATE_MULTIPLE_ISSUANCE_PENDING
            )

        cred_request_message = V20CredRequest(
            comment=comment,
            formats=[format for (format, _) in request_formats],
            requests_attach=[attach for (_, attach) in request_formats],
        )

        # Assign thid (and optionally pthid) to message
        cred_request_message.assign_thread_from(cred_ex_record.cred_offer)
        cred_request_message.assign_trace_decorator(
            self._profile.settings, cred_ex_record.trace
        )

        cred_ex_record.thread_id = cred_request_message._thread_id
        cred_ex_record.state = V20CredExRecord.STATE_REQUEST_SENT
        if cred_request_exists:
            existing_cred_request = cred_ex_record.cred_request
            for fmt, atch in request_formats:
                existing_cred_request.add_attachments(fmt, atch)
            cred_ex_record.cred_request = existing_cred_request
            cred_ex_record.multiple_credentials = True
        else:
            cred_ex_record.cred_request = cred_request_message

        async with self._profile.session() as session:
            await cred_ex_record.save(session, reason="create v2.0 credential request")

        return (cred_ex_record, cred_request_message)

    async def receive_request(
        self,
        cred_request_message: V20CredRequest,
        connection_record: Optional[ConnRecord],
        oob_record: Optional[OobRecord],
    ) -> V20CredExRecord:
        """
        Receive a credential request.

        Args:
            cred_request_message: credential request to receive
            connection_id: connection identifier

        Returns:
            credential exchange record, updated

        """
        # connection_id is None in the record if this is in response to
        # an request~attach from an OOB message. If so, we do not want to filter
        # the record by connection_id.
        connection_id = None if oob_record else connection_record.connection_id

        async with self._profile.session() as session:
            try:
                cred_ex_record = await V20CredExRecord.retrieve_by_conn_and_thread(
                    session,
                    connection_id,
                    cred_request_message._thread_id,
                    role=V20CredExRecord.ROLE_ISSUER,
                )
            except StorageNotFoundError:
                # holder sent this request free of any offer
                cred_ex_record = V20CredExRecord(
                    connection_id=connection_id,
                    thread_id=cred_request_message._thread_id,
                    initiator=V20CredExRecord.INITIATOR_EXTERNAL,
                    role=V20CredExRecord.ROLE_ISSUER,
                    auto_remove=not self._profile.settings.get(
                        "preserve_exchange_records"
                    ),
                    trace=(cred_request_message._trace is not None),
                    auto_issue=self._profile.settings.get(
                        "debug.auto_respond_credential_request"
                    ),
                )

        if connection_record:
            cred_ex_record.connection_id = connection_record.connection_id

        if cred_ex_record.multiple_issuance_state:
            if (
                cred_ex_record.multiple_issuance_state
                != V20CredExRecord.STATE_MULTIPLE_ISSUANCE_COMPLETE
                or cred_ex_record.multiple_issuance_state
                != V20CredExRecord.STATE_MULTIPLE_ISSUANCE_ABANDONED
            ):
                raise V20CredManagerError(
                    f"Credential exchange {cred_ex_record.cred_ex_id} "
                    f"in {cred_ex_record.multiple_issuance_state} "
                    "multiple_issuance_state"
                )

        handled_formats = []
        for format in cred_request_message.formats:
            cred_format = V20CredFormat.Format.get(format.format)
            if cred_format:
                await cred_format.handler(self.profile).receive_request(
                    cred_ex_record, cred_request_message
                )
                handled_formats.append(cred_format)

        if len(handled_formats) == 0:
            raise V20CredManagerError("No supported credential formats received.")
        elif len(handled_formats) >= 2:
            cred_ex_record.multiple_credentials = True
            cred_ex_record.multiple_issuance_state = (
                V20CredExRecord.STATE_MULTIPLE_ISSUANCE_PENDING
            )

        if cred_ex_record.cred_request:
            existing_cred_request = cred_ex_record.cred_request
            for iter in range(len(cred_request_message.requests_attach)):
                existing_cred_request.add_attachments(
                    cred_request_message.formats[iter],
                    cred_request_message.requests_attach[iter],
                )
            cred_ex_record.cred_request = existing_cred_request
            cred_ex_record.multiple_credentials = True
        else:
            cred_ex_record.cred_request = cred_request_message
        cred_ex_record.state = V20CredExRecord.STATE_REQUEST_RECEIVED

        async with self._profile.session() as session:
            await cred_ex_record.save(session, reason="receive v2.0 credential request")

        return cred_ex_record

    async def issue_credential(
        self,
        cred_ex_record: V20CredExRecord,
        *,
        comment: str = None,
        more_available: int = 0,
    ) -> Tuple[V20CredExRecord, V20CredIssue]:
        """
        Issue a credential.

        Args:
            cred_ex_record: credential exchange record for which to issue credential
            comment: optional human-readable comment pertaining to credential issue
            more_available: Count of the verifiable credential type for the Holder
                that the Issuer is willing to issue
        Returns:
            Tuple: (Updated credential exchange record, credential issue message)

        """

        if cred_ex_record.state != V20CredExRecord.STATE_REQUEST_RECEIVED:
            raise V20CredManagerError(
                f"Credential exchange {cred_ex_record.cred_ex_id} "
                f"in {cred_ex_record.state} state "
                f"(must be {V20CredExRecord.STATE_REQUEST_RECEIVED})"
            )

        if cred_ex_record.multiple_issuance_state:
            if (
                cred_ex_record.multiple_issuance_state
                != V20CredExRecord.STATE_MULTIPLE_ISSUANCE_COMPLETE
                or cred_ex_record.multiple_issuance_state
                != V20CredExRecord.STATE_MULTIPLE_ISSUANCE_ABANDONED
            ):
                raise V20CredManagerError(
                    f"Credential exchange {cred_ex_record.cred_ex_id} "
                    f"in {cred_ex_record.multiple_issuance_state} "
                    "multiple_issuance_state "
                )

        cred_issue_exists = False
        if cred_ex_record.cred_issue:
            if cred_ex_record.multiple_credentials:
                cred_issue_exists = True
            else:
                raise V20CredManagerError(
                    "issue_credential() called multiple times for "
                    f"cred ex record {cred_ex_record.cred_ex_id}"
                )

        replacement_id = None
        input_formats = cred_ex_record.cred_request.formats

        if cred_ex_record.cred_offer:
            cred_offer_message = cred_ex_record.cred_offer
            replacement_id = cred_offer_message.replacement_id

        # Format specific issue_credential handler
        issue_formats = []
        to_exclude = cred_ex_record.processed_attach_ids
        for format in input_formats:
            cred_format = V20CredFormat.Format.get(format.format)
            if cred_format:
                attach_id = (
                    format.attach_id if format.attach_id != cred_format.api else None
                )
                if attach_id and attach_id in to_exclude:
                    continue
                issue_formats.append(
                    await cred_format.handler(self.profile).issue_credential(
                        cred_ex_record=cred_ex_record, attach_id=attach_id
                    )
                )
                if attach_id:
                    cred_ex_record.process_attach_id(attach_id)

        if len(issue_formats) == 0:
            raise V20CredManagerError(
                "Unable to issue credential. No supported formats"
            )

        cred_issue_message = V20CredIssue(
            replacement_id=replacement_id,
            comment=comment,
            formats=[format for (format, _) in issue_formats],
            credentials_attach=[attach for (_, attach) in issue_formats],
            more_available=more_available,
        )
        if not more_available or more_available == 0:
            cred_ex_record.state = V20CredExRecord.STATE_ISSUED
            if cred_ex_record.multiple_credentials:
                cred_ex_record.multiple_issuance_state = (
                    V20CredExRecord.STATE_MULTIPLE_ISSUANCE_COMPLETE
                )
        else:
            cred_ex_record.state = V20CredExRecord.STATE_OFFER_SENT
            cred_ex_record.multiple_issuance_state = (
                V20CredExRecord.STATE_MULTIPLE_ISSUANCE_PENDING
            )
            cred_ex_record.multiple_credentials = True
        if cred_issue_exists:
            existing_cred_issue = cred_ex_record.cred_issue
            for iter in range(len(cred_issue_message.credentials_attach)):
                existing_cred_issue.add_attachments(
                    cred_issue_message.formats[iter],
                    cred_issue_message.credentials_attach[iter],
                )
            cred_ex_record.cred_issue = existing_cred_issue
            cred_ex_record.multiple_credentials = True
        else:
            cred_ex_record.cred_issue = cred_issue_message
        async with self._profile.session() as session:
            # FIXME - re-fetch record to check state, apply transactional update
            await cred_ex_record.save(session, reason="v2.0 issue credential")

        cred_issue_message._thread = {"thid": cred_ex_record.thread_id}
        cred_issue_message.assign_trace_decorator(
            self._profile.settings, cred_ex_record.trace
        )

        return (cred_ex_record, cred_issue_message)

    async def receive_credential(
        self,
        cred_issue_message: V20CredIssue,
        connection_id: Optional[str],
    ) -> V20CredExRecord:
        """
        Receive a credential issue message from an issuer.

        Hold cred in storage potentially to be processed by controller before storing.

        Returns:
            Credential exchange record, retrieved and updated

        """
        assert cred_issue_message.credentials_attach

        # FIXME use transaction, fetch for_update
        async with self._profile.session() as session:
            cred_ex_record = await V20CredExRecord.retrieve_by_conn_and_thread(
                session,
                connection_id,
                cred_issue_message._thread_id,
                role=V20CredExRecord.ROLE_HOLDER,
            )

        if cred_ex_record.multiple_issuance_state:
            if (
                cred_ex_record.multiple_issuance_state
                != V20CredExRecord.STATE_MULTIPLE_ISSUANCE_COMPLETE
                or cred_ex_record.multiple_issuance_state
                != V20CredExRecord.STATE_MULTIPLE_ISSUANCE_ABANDONED
            ):
                raise V20CredManagerError(
                    f"Credential exchange {cred_ex_record.cred_ex_id} "
                    f"in {cred_ex_record.multiple_issuance_state} "
                    "multiple_issuance_state"
                )

        cred_request_message = cred_ex_record.cred_request
        req_format_ids = [
            fmt.attach_id
            for fmt in cred_request_message.formats
            if V20CredFormat.Format.get(fmt.format)
        ]
        issue_format_ids = [
            fmt.attach_id
            for fmt in cred_issue_message.formats
            if V20CredFormat.Format.get(fmt.format)
        ]
        alrady_processed_attach = cred_ex_record.processed_attach_ids
        issue_formats = cred_issue_message.formats
        handled_formats = []
        more_available = cred_issue_message.more_available
        # check that we didn't receive any formats not present in the request
        if set(issue_format_ids + alrady_processed_attach) - set(req_format_ids):
            raise V20CredManagerError(
                "Received issue credential format(s) not "
                "present in credential request: "
                f"{set(issue_format_ids + alrady_processed_attach) - set(req_format_ids)}"
            )
        for issue_format in issue_formats:
            cred_format = V20CredFormat.Format.get(issue_format.format)
            if cred_format:
                attach_id = (
                    issue_format.attach_id
                    if issue_format.attach_id != cred_format.api
                    else None
                )
                if attach_id and attach_id in alrady_processed_attach:
                    continue
                await cred_format.handler(self.profile).receive_credential(
                    cred_ex_record, cred_issue_message, attach_id
                )
                if attach_id:
                    cred_ex_record.process_attach_id(attach_id)
                handled_formats.append(cred_format)

        if len(handled_formats) == 0:
            raise V20CredManagerError("No supported credential formats received.")

        if cred_ex_record.cred_issue:
            existing_cred_issue = cred_ex_record.cred_issue

            for iter in range(len(cred_issue_message.credentials_attach)):
                existing_cred_issue.add_attachments(
                    cred_issue_message.formats[iter],
                    cred_issue_message.credentials_attach[iter],
                )
            cred_ex_record.cred_issue = existing_cred_issue
            cred_ex_record.multiple_credentials = True
        else:
            cred_ex_record.cred_issue = cred_issue_message
        disable_multiple_cred_flow = self._profile.settings.get(
            "debug.disable_multiple_credential_flow"
        )
        if more_available and more_available > 0:
            if disable_multiple_cred_flow:
                cred_ex_record.state = V20CredExRecord.STATE_CREDENTIAL_RECEIVED
                responder = self._profile.inject_or(BaseResponder)
                if responder:
                    report = V20CredProblemReport(
                        description={
                            "en": (
                                "Holder requests no more credentials "
                                "of this type to be issued."
                            ),
                            "code": (
                                ProblemReportReason.STOP_MORE_CREDENTIAL_ISSUANCE.value
                            ),
                        }
                    )
                    if cred_ex_record.thread_id:
                        report.assign_thread_id(cred_ex_record.thread_id)
                    await responder.send_reply(
                        report, connection_id=cred_ex_record.connection_id
                    )
                cred_ex_record.multiple_issuance_state = (
                    V20CredExRecord.STATE_MULTIPLE_ISSUANCE_ABANDONED
                )
            else:
                cred_ex_record.state = V20CredExRecord.STATE_OFFER_RECEIVED
                cred_ex_record.multiple_issuance_state = (
                    V20CredExRecord.STATE_MULTIPLE_ISSUANCE_PENDING
                )
        else:
            cred_ex_record.state = V20CredExRecord.STATE_CREDENTIAL_RECEIVED
            cred_ex_record.multiple_issuance_state = (
                V20CredExRecord.STATE_MULTIPLE_ISSUANCE_COMPLETE
            )

        async with self._profile.session() as session:
            await cred_ex_record.save(session, reason="receive v2.0 credential issue")
        return cred_ex_record

    async def store_credential(
        self, cred_ex_record: V20CredExRecord, cred_id: str = None
    ) -> Tuple[V20CredExRecord, V20CredAck]:
        """
        Store a credential in holder wallet; send ack to issuer.

        Args:
            cred_ex_record: credential exchange record with credential to store and ack
            cred_id: optional credential identifier to override default on storage

        Returns:
            Updated credential exchange record

        """
        if cred_ex_record.state != (V20CredExRecord.STATE_CREDENTIAL_RECEIVED):
            raise V20CredManagerError(
                f"Credential exchange {cred_ex_record.cred_ex_id} "
                f"in {cred_ex_record.state} state "
                f"(must be {V20CredExRecord.STATE_CREDENTIAL_RECEIVED})"
            )
        to_exclude = cred_ex_record.stored_attach_ids
        # Format specific store_credential handler
        for format in cred_ex_record.cred_issue.formats:
            cred_format = V20CredFormat.Format.get(format.format)
            attach_id = (
                format.attach_id if format.attach_id != cred_format.api else None
            )
            if cred_format:
                await cred_format.handler(self.profile).store_credential(
                    cred_ex_record, cred_id, attach_id
                )
                # TODO: if storing multiple credentials we can't reuse the same id
                cred_id = None
                if attach_id and attach_id not in to_exclude:
                    cred_ex_record.store_attach_id(attach_id)

        return cred_ex_record

    async def send_cred_ack(
        self,
        cred_ex_record: V20CredExRecord,
    ):
        """
        Create, send, and return ack message for input cred ex record.

        Delete cred ex record if set to auto-remove.

        Returns:
            Tuple: cred ex record, cred ack message for tracing

        """
        cred_ack_message = V20CredAck()
        cred_ack_message.assign_thread_id(
            cred_ex_record.thread_id, cred_ex_record.parent_thread_id
        )
        cred_ack_message.assign_trace_decorator(
            self._profile.settings, cred_ex_record.trace
        )

        cred_ex_record.state = V20CredExRecord.STATE_DONE
        try:
            async with self._profile.session() as session:
                # FIXME - re-fetch record to check state, apply transactional update
                await cred_ex_record.save(session, reason="store credential v2.0")

            if cred_ex_record.auto_remove:
                await self.delete_cred_ex_record(cred_ex_record.cred_ex_id)

        except StorageError:
            LOGGER.exception(
                "Error sending credential ack"
            )  # holder still owes an ack: carry on

        responder = self._profile.inject_or(BaseResponder)
        if responder:
            await responder.send_reply(
                cred_ack_message,
                connection_id=cred_ex_record.connection_id,
            )
        else:
            LOGGER.warning(
                "Configuration has no BaseResponder: cannot ack credential on %s",
                cred_ex_record.thread_id,
            )

        return cred_ex_record, cred_ack_message

    async def receive_credential_ack(
        self, cred_ack_message: V20CredAck, connection_id: Optional[str]
    ) -> V20CredExRecord:
        """
        Receive credential ack from holder.

        Args:
            cred_ack_message: credential ack message to receive
            connection_id: connection identifier

        Returns:
            credential exchange record, retrieved and updated

        """
        # FIXME use transaction, fetch for_update
        async with self._profile.session() as session:
            cred_ex_record = await V20CredExRecord.retrieve_by_conn_and_thread(
                session,
                connection_id,
                cred_ack_message._thread_id,
                role=V20CredExRecord.ROLE_ISSUER,
            )

            cred_ex_record.state = V20CredExRecord.STATE_DONE
            await cred_ex_record.save(session, reason="receive credential ack v2.0")

        if cred_ex_record.auto_remove:
            await self.delete_cred_ex_record(cred_ex_record.cred_ex_id)

        return cred_ex_record

    async def delete_cred_ex_record(self, cred_ex_id: str) -> None:
        """Delete credential exchange record and associated detail records."""

        async with self._profile.session() as session:
            for fmt in V20CredFormat.Format:  # details first: do not strand any orphans
                for record in await fmt.detail.query_by_cred_ex_id(
                    session,
                    cred_ex_id,
                ):
                    await record.delete_record(session)

            cred_ex_record = await V20CredExRecord.retrieve_by_id(session, cred_ex_id)
            await cred_ex_record.delete_record(session)

    async def receive_problem_report(
        self, message: V20CredProblemReport, connection_id: str
    ):
        """
        Receive problem report.

        Returns:
            credential exchange record, retrieved and updated

        """
        # FIXME use transaction, fetch for_update
        async with self._profile.session() as session:
            cred_ex_record = await V20CredExRecord.retrieve_by_conn_and_thread(
                session,
                connection_id,
                message._thread_id,
            )

            code = message.description.get(
                "code",
                ProblemReportReason.ISSUANCE_ABANDONED.value,
            )
            if code == ProblemReportReason.ISSUANCE_ABANDONED.value:
                cred_ex_record.state = V20CredExRecord.STATE_ABANDONED
            elif code == ProblemReportReason.STOP_MORE_CREDENTIAL_ISSUANCE.value:
                cred_ex_record.multiple_issuance_state = (
                    V20CredExRecord.STATE_MULTIPLE_ISSUANCE_ABANDONED
                )
            cred_ex_record.error_msg = f"{code}: {message.description.get('en', code)}"
            await cred_ex_record.save(session, reason="received problem report")

        return cred_ex_record
