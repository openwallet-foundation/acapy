"""Classes to manage presentations."""

import logging

from typing import Optional, Tuple

from ...out_of_band.v1_0.models.oob_record import OobRecord
from ....connections.models.conn_record import ConnRecord
from ....core.error import BaseError
from ....core.profile import Profile
from ....messaging.responder import BaseResponder

from .messages.pres import V20Pres
from .messages.pres_ack import V20PresAck
from .messages.pres_format import V20PresFormat
from .messages.pres_problem_report import V20PresProblemReport, ProblemReportReason
from .messages.pres_proposal import V20PresProposal
from .messages.pres_request import V20PresRequest
from .models.pres_exchange import V20PresExRecord


LOGGER = logging.getLogger(__name__)


class V20PresManagerError(BaseError):
    """Presentation error."""


class V20PresManager:
    """Class for managing presentations."""

    def __init__(self, profile: Profile):
        """
        Initialize a V20PresManager.

        Args:
            profile: The profile instance for this presentation manager
        """

        self._profile = profile

    async def create_exchange_for_proposal(
        self,
        connection_id: str,
        pres_proposal_message: V20PresProposal,
        auto_present: bool = None,
        auto_remove: bool = None,
    ):
        """
        Create a presentation exchange record for input presentation proposal.

        Args:
            connection_id: connection identifier
            pres_proposal_message: presentation proposal to serialize
                to exchange record
            auto_present: whether to present proof upon receiving proof request
                (default to configuration setting)
            auto_remove: whether to remove this presentation exchange upon completion

        Returns:
            Presentation exchange record, created

        """
        if auto_remove is None:
            auto_remove = not self._profile.settings.get("preserve_exchange_records")
        pres_ex_record = V20PresExRecord(
            connection_id=connection_id,
            thread_id=pres_proposal_message._thread_id,
            initiator=V20PresExRecord.INITIATOR_SELF,
            role=V20PresExRecord.ROLE_PROVER,
            state=V20PresExRecord.STATE_PROPOSAL_SENT,
            pres_proposal=pres_proposal_message,
            auto_present=auto_present,
            trace=(pres_proposal_message._trace is not None),
            auto_remove=auto_remove,
        )

        async with self._profile.session() as session:
            await pres_ex_record.save(
                session, reason="create v2.0 presentation proposal"
            )

        return pres_ex_record

    async def receive_pres_proposal(
        self, message: V20PresProposal, conn_record: ConnRecord
    ):
        """
        Receive a presentation proposal from message in context on manager creation.

        Returns:
            Presentation exchange record, created

        """
        pres_ex_record = V20PresExRecord(
            connection_id=conn_record.connection_id,
            thread_id=message._thread_id,
            initiator=V20PresExRecord.INITIATOR_EXTERNAL,
            role=V20PresExRecord.ROLE_VERIFIER,
            state=V20PresExRecord.STATE_PROPOSAL_RECEIVED,
            pres_proposal=message,
            trace=(message._trace is not None),
            auto_remove=not self._profile.settings.get("preserve_exchange_records"),
        )

        async with self._profile.session() as session:
            await pres_ex_record.save(
                session, reason="receive v2.0 presentation request"
            )

        return pres_ex_record

    async def create_bound_request(
        self,
        pres_ex_record: V20PresExRecord,
        request_data: dict = None,
        comment: str = None,
    ):
        """
        Create a presentation request bound to a proposal.

        Args:
            pres_ex_record: Presentation exchange record for which
                to create presentation request
            comment: Optional human-readable comment pertaining to request creation

        Returns:
            A tuple (updated presentation exchange record, presentation request message)

        """
        proof_proposal = pres_ex_record.pres_proposal
        input_formats = proof_proposal.formats
        request_formats = []
        for format in input_formats:
            pres_exch_format = V20PresFormat.Format.get(format.format)

            if pres_exch_format:
                request_formats.append(
                    await pres_exch_format.handler(self._profile).create_bound_request(
                        pres_ex_record,
                        request_data,
                    )
                )
        if len(request_formats) == 0:
            raise V20PresManagerError(
                "Unable to create presentation request. No supported formats"
            )
        pres_request_message = V20PresRequest(
            comment=comment,
            will_confirm=True,
            formats=[format for (format, _) in request_formats],
            request_presentations_attach=[attach for (_, attach) in request_formats],
        )
        pres_request_message._thread = {"thid": pres_ex_record.thread_id}
        pres_request_message.assign_trace_decorator(
            self._profile.settings, pres_ex_record.trace
        )

        pres_ex_record.thread_id = pres_request_message._thread_id
        pres_ex_record.state = V20PresExRecord.STATE_REQUEST_SENT
        pres_ex_record.pres_request = pres_request_message
        async with self._profile.session() as session:
            await pres_ex_record.save(
                session, reason="create (bound) v2.0 presentation request"
            )

        return pres_ex_record, pres_request_message

    async def create_exchange_for_request(
        self,
        connection_id: str,
        pres_request_message: V20PresRequest,
        auto_verify: bool = None,
        auto_remove: bool = None,
    ):
        """
        Create a presentation exchange record for input presentation request.

        Args:
            connection_id: connection identifier
            pres_request_message: presentation request to use in creating
                exchange record, extracting indy proof request and thread id
            auto_verify: whether to auto-verify presentation exchange
            auto_remove: whether to remove this presentation exchange upon completion

        Returns:
            Presentation exchange record, updated

        """
        if auto_remove is None:
            auto_remove = not self._profile.settings.get("preserve_exchange_records")
        pres_ex_record = V20PresExRecord(
            connection_id=connection_id,
            thread_id=pres_request_message._thread_id,
            initiator=V20PresExRecord.INITIATOR_SELF,
            role=V20PresExRecord.ROLE_VERIFIER,
            state=V20PresExRecord.STATE_REQUEST_SENT,
            pres_request=pres_request_message,
            auto_verify=auto_verify,
            trace=(pres_request_message._trace is not None),
            auto_remove=auto_remove,
        )
        async with self._profile.session() as session:
            await pres_ex_record.save(
                session, reason="create (free) v2.0 presentation request"
            )

        return pres_ex_record

    async def receive_pres_request(self, pres_ex_record: V20PresExRecord):
        """
        Receive a presentation request.

        Args:
            pres_ex_record: presentation exchange record with request to receive

        Returns:
            The presentation exchange record, updated

        """
        pres_ex_record.state = V20PresExRecord.STATE_REQUEST_RECEIVED
        async with self._profile.session() as session:
            await pres_ex_record.save(
                session, reason="receive v2.0 presentation request"
            )

        return pres_ex_record

    async def create_pres(
        self,
        pres_ex_record: V20PresExRecord,
        request_data: dict = {},
        *,
        comment: str = None,
    ) -> Tuple[V20PresExRecord, V20Pres]:
        """
        Create a presentation.

        Args:
            pres_ex_record: record to update
            requested_credentials: indy formatted requested_credentials
            comment: optional human-readable comment
            format_: presentation format

        Example `requested_credentials` format, mapping proof request referents (uuid)
        to wallet referents (cred id):

        ::

            {
                "self_attested_attributes": {
                    "j233ffbc-bd35-49b1-934f-51e083106f6d": "value"
                },
                "requested_attributes": {
                    "6253ffbb-bd35-49b3-934f-46e083106f6c": {
                        "cred_id": "5bfa40b7-062b-4ae0-a251-a86c87922c0e",
                        "revealed": true
                    }
                },
                "requested_predicates": {
                    "bfc8a97d-60d3-4f21-b998-85eeabe5c8c0": {
                        "cred_id": "5bfa40b7-062b-4ae0-a251-a86c87922c0e"
                    }
                }
            }

        Returns:
            A tuple (updated presentation exchange record, presentation message)

        """
        proof_request = pres_ex_record.pres_request
        input_formats = proof_request.formats
        pres_formats = []
        for format in input_formats:
            pres_exch_format = V20PresFormat.Format.get(format.format)

            if pres_exch_format:
                if not request_data:
                    request_data_pres_exch = {}
                else:
                    request_data_pres_exch = {
                        pres_exch_format.api: request_data.get(pres_exch_format.api)
                    }
                pres_tuple = await pres_exch_format.handler(self._profile).create_pres(
                    pres_ex_record,
                    request_data_pres_exch,
                )
                if pres_tuple:
                    pres_formats.append(pres_tuple)
                else:
                    raise V20PresManagerError(
                        "Unable to create presentation. ProblemReport message sent"
                    )
        if len(pres_formats) == 0:
            raise V20PresManagerError(
                "Unable to create presentation. No supported formats"
            )
        pres_message = V20Pres(
            comment=comment,
            formats=[format for (format, _) in pres_formats],
            presentations_attach=[attach for (_, attach) in pres_formats],
        )

        # Assign thid (and optionally pthid) to message
        pres_message.assign_thread_from(pres_ex_record.pres_request)
        pres_message.assign_trace_decorator(
            self._profile.settings, pres_ex_record.trace
        )

        # save presentation exchange state
        pres_ex_record.state = V20PresExRecord.STATE_PRESENTATION_SENT
        pres_ex_record.pres = V20Pres(
            formats=[format for (format, _) in pres_formats],
            presentations_attach=[attach for (_, attach) in pres_formats],
        )
        async with self._profile.session() as session:
            await pres_ex_record.save(session, reason="create v2.0 presentation")
        return pres_ex_record, pres_message

    async def receive_pres(
        self,
        message: V20Pres,
        connection_record: Optional[ConnRecord],
        oob_record: Optional[OobRecord],
    ):
        """
        Receive a presentation, from message in context on manager creation.

        Returns:
            presentation exchange record, retrieved and updated

        """

        thread_id = message._thread_id
        # Normally we only set the connection_id to None if an oob record is present
        # But present proof supports the old-style AIP-1 connectionless exchange that
        # bypasses the oob record. So we can't verify if an oob record is associated with
        # the exchange because it is possible that there is None
        connection_id = (
            None
            if oob_record
            else connection_record.connection_id
            if connection_record
            else None
        )

        async with self._profile.session() as session:
            pres_ex_record = await V20PresExRecord.retrieve_by_tag_filter(
                session,
                {"thread_id": thread_id},
                {
                    "role": V20PresExRecord.ROLE_VERIFIER,
                    "connection_id": connection_id,
                },
            )

        # Save connection id (if it wasn't already present)
        if connection_record:
            pres_ex_record.connection_id = connection_record.connection_id

        input_formats = message.formats

        for format in input_formats:
            pres_format = V20PresFormat.Format.get(format.format)

            if pres_format:
                receive_pres_return = await pres_format.handler(
                    self._profile
                ).receive_pres(
                    message,
                    pres_ex_record,
                )
                if isinstance(receive_pres_return, bool) and not receive_pres_return:
                    raise V20PresManagerError(
                        "Unable to verify received presentation."
                        " ProblemReport message sent"
                    )
        pres_ex_record.pres = message
        pres_ex_record.state = V20PresExRecord.STATE_PRESENTATION_RECEIVED
        async with self._profile.session() as session:
            await pres_ex_record.save(session, reason="receive v2.0 presentation")

        return pres_ex_record

    async def verify_pres(
        self, pres_ex_record: V20PresExRecord, responder: Optional[BaseResponder] = None
    ):
        """
        Verify a presentation.

        Args:
            pres_ex_record: presentation exchange record
                with presentation request and presentation to verify

        Returns:
            presentation exchange record, updated

        """
        pres_request_msg = pres_ex_record.pres_request
        input_formats = pres_request_msg.formats
        for format in input_formats:
            pres_exch_format = V20PresFormat.Format.get(format.format)

            if pres_exch_format:
                pres_ex_record = await pres_exch_format.handler(
                    self._profile
                ).verify_pres(
                    pres_ex_record,
                )
                if pres_ex_record.verified == "false":
                    break

        pres_ex_record.state = V20PresExRecord.STATE_DONE

        async with self._profile.session() as session:
            await pres_ex_record.save(session, reason="verify v2.0 presentation")

        if pres_request_msg.will_confirm:
            await self.send_pres_ack(pres_ex_record, responder)

        return pres_ex_record

    async def send_pres_ack(
        self, pres_ex_record: V20PresExRecord, responder: Optional[BaseResponder] = None
    ):
        """
        Send acknowledgement of presentation receipt.

        Args:
            pres_ex_record: presentation exchange record with thread id

        """
        responder = responder or self._profile.inject_or(BaseResponder)

        if responder:
            pres_ack_message = V20PresAck(verification_result=pres_ex_record.verified)
            pres_ack_message._thread = {"thid": pres_ex_record.thread_id}
            pres_ack_message.assign_trace_decorator(
                self._profile.settings, pres_ex_record.trace
            )

            await responder.send_reply(
                pres_ack_message,
                # connection_id can be none in case of connectionless
                connection_id=pres_ex_record.connection_id,
            )

            # all done: delete
            if pres_ex_record.auto_remove:
                async with self._profile.session() as session:
                    await pres_ex_record.delete_record(session)
        else:
            LOGGER.warning(
                "Configuration has no BaseResponder: cannot ack presentation on %s",
                pres_ex_record.thread_id,
            )

    async def receive_pres_ack(self, message: V20PresAck, conn_record: ConnRecord):
        """
        Receive a presentation ack, from message in context on manager creation.

        Returns:
            presentation exchange record, retrieved and updated

        """
        connection_id = conn_record.connection_id if conn_record else None
        async with self._profile.session() as session:
            pres_ex_record = await V20PresExRecord.retrieve_by_tag_filter(
                session,
                {"thread_id": message._thread_id},
                {
                    # connection_id can be null in connectionless
                    "connection_id": connection_id,
                    "role": V20PresExRecord.ROLE_PROVER,
                },
            )
            pres_ex_record.verified = message._verification_result
            pres_ex_record.state = V20PresExRecord.STATE_DONE

            await pres_ex_record.save(session, reason="receive v2.0 presentation ack")

            # all done: delete
            if pres_ex_record.auto_remove:
                async with self._profile.session() as session:
                    await pres_ex_record.delete_record(session)

        return pres_ex_record

    async def receive_problem_report(
        self, message: V20PresProblemReport, connection_id: str
    ):
        """
        Receive problem report.

        Returns:
            presentation exchange record, retrieved and updated

        """
        # FIXME use transaction, fetch for_update
        async with self._profile.session() as session:
            pres_ex_record = await V20PresExRecord.retrieve_by_tag_filter(
                session,
                {"thread_id": message._thread_id},
                {"connection_id": connection_id},
            )

            pres_ex_record.state = V20PresExRecord.STATE_ABANDONED
            code = message.description.get("code", ProblemReportReason.ABANDONED.value)
            pres_ex_record.error_msg = f"{code}: {message.description.get('en', code)}"
            await pres_ex_record.save(session, reason="received problem report")

        return pres_ex_record
