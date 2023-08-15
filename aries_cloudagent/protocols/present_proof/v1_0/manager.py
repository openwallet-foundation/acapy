"""Classes to manage presentations."""

import json
import logging
from typing import Optional

from ...out_of_band.v1_0.models.oob_record import OobRecord
from ....connections.models.conn_record import ConnRecord
from ....core.error import BaseError
from ....core.profile import Profile
from ....indy.verifier import IndyVerifier
from ....messaging.decorators.attach_decorator import AttachDecorator
from ....messaging.responder import BaseResponder
from ....storage.error import StorageNotFoundError
from ..indy.pres_exch_handler import IndyPresExchHandler

from .messages.presentation_ack import PresentationAck
from .messages.presentation_problem_report import (
    PresentationProblemReport,
    ProblemReportReason,
)
from .messages.presentation_proposal import PresentationProposal
from .messages.presentation_request import PresentationRequest
from .messages.presentation import Presentation
from .message_types import ATTACH_DECO_IDS, PRESENTATION, PRESENTATION_REQUEST
from .models.presentation_exchange import V10PresentationExchange

LOGGER = logging.getLogger(__name__)


class PresentationManagerError(BaseError):
    """Presentation error."""


class PresentationManager:
    """Class for managing presentations."""

    def __init__(self, profile: Profile):
        """
        Initialize a PresentationManager.

        Args:
            profile: The profile instance for this presentation manager
        """

        self._profile = profile

    async def create_exchange_for_proposal(
        self,
        connection_id: str,
        presentation_proposal_message: PresentationProposal,
        auto_present: bool = None,
        auto_remove: bool = None,
    ):
        """
        Create a presentation exchange record for input presentation proposal.

        Args:
            connection_id: connection identifier
            presentation_proposal_message: presentation proposal to serialize
                to exchange record
            auto_present: whether to present proof upon receiving proof request
                (default to configuration setting)
            auto_remove: whether to remove this presentation exchange upon completion

        Returns:
            Presentation exchange record, created

        """
        if auto_remove is None:
            auto_remove = not self._profile.settings.get("preserve_exchange_records")
        presentation_exchange_record = V10PresentationExchange(
            connection_id=connection_id,
            thread_id=presentation_proposal_message._thread_id,
            initiator=V10PresentationExchange.INITIATOR_SELF,
            role=V10PresentationExchange.ROLE_PROVER,
            state=V10PresentationExchange.STATE_PROPOSAL_SENT,
            presentation_proposal_dict=presentation_proposal_message,
            auto_present=auto_present,
            trace=(presentation_proposal_message._trace is not None),
            auto_remove=auto_remove,
        )
        async with self._profile.session() as session:
            await presentation_exchange_record.save(
                session, reason="create presentation proposal"
            )

        return presentation_exchange_record

    async def receive_proposal(
        self, message: PresentationProposal, connection_record: ConnRecord
    ):
        """
        Receive a presentation proposal from message in context on manager creation.

        Returns:
            Presentation exchange record, created

        """
        presentation_exchange_record = V10PresentationExchange(
            connection_id=connection_record.connection_id,
            thread_id=message._thread_id,
            initiator=V10PresentationExchange.INITIATOR_EXTERNAL,
            role=V10PresentationExchange.ROLE_VERIFIER,
            state=V10PresentationExchange.STATE_PROPOSAL_RECEIVED,
            presentation_proposal_dict=message,
            trace=(message._trace is not None),
            auto_remove=not self._profile.settings.get("preserve_exchange_records"),
        )
        async with self._profile.session() as session:
            await presentation_exchange_record.save(
                session, reason="receive presentation request"
            )

        return presentation_exchange_record

    async def create_bound_request(
        self,
        presentation_exchange_record: V10PresentationExchange,
        name: str = None,
        version: str = None,
        nonce: str = None,
        comment: str = None,
    ):
        """
        Create a presentation request bound to a proposal.

        Args:
            presentation_exchange_record: Presentation exchange record for which
                to create presentation request
            name: name to use in presentation request (None for default)
            version: version to use in presentation request (None for default)
            nonce: nonce to use in presentation request (None to generate)
            comment: Optional human-readable comment pertaining to request creation

        Returns:
            A tuple (updated presentation exchange record, presentation request message)

        """
        indy_proof_request = await (
            presentation_exchange_record.presentation_proposal_dict
        ).presentation_proposal.indy_proof_request(
            name=name,
            version=version,
            nonce=nonce,
            profile=self._profile,
        )
        presentation_request_message = PresentationRequest(
            comment=comment,
            request_presentations_attach=[
                AttachDecorator.data_base64(
                    mapping=indy_proof_request,
                    ident=ATTACH_DECO_IDS[PRESENTATION_REQUEST],
                )
            ],
        )
        presentation_request_message._thread = {
            "thid": presentation_exchange_record.thread_id
        }
        presentation_request_message.assign_trace_decorator(
            self._profile.settings, presentation_exchange_record.trace
        )

        presentation_exchange_record.thread_id = presentation_request_message._thread_id
        presentation_exchange_record.state = V10PresentationExchange.STATE_REQUEST_SENT
        presentation_exchange_record.presentation_request = indy_proof_request
        async with self._profile.session() as session:
            await presentation_exchange_record.save(
                session, reason="create (bound) presentation request"
            )

        return presentation_exchange_record, presentation_request_message

    async def create_exchange_for_request(
        self,
        connection_id: str,
        presentation_request_message: PresentationRequest,
        auto_verify: bool = None,
        auto_remove: bool = None,
    ):
        """
        Create a presentation exchange record for input presentation request.

        Args:
            connection_id: connection identifier
            presentation_request_message: presentation request to use in creating
                exchange record, extracting indy proof request and thread id
            auto_verify: whether to auto-verify presentation exchange
            auto_remove: whether to remove this presentation exchange upon completion
        Returns:
            Presentation exchange record, updated

        """
        if auto_remove is None:
            auto_remove = not self._profile.settings.get("preserve_exchange_records")
        presentation_exchange_record = V10PresentationExchange(
            connection_id=connection_id,
            thread_id=presentation_request_message._thread_id,
            initiator=V10PresentationExchange.INITIATOR_SELF,
            role=V10PresentationExchange.ROLE_VERIFIER,
            state=V10PresentationExchange.STATE_REQUEST_SENT,
            presentation_request=presentation_request_message.indy_proof_request(),
            presentation_request_dict=presentation_request_message,
            auto_verify=auto_verify,
            trace=(presentation_request_message._trace is not None),
            auto_remove=auto_remove,
        )
        async with self._profile.session() as session:
            await presentation_exchange_record.save(
                session, reason="create (free) presentation request"
            )

        return presentation_exchange_record

    async def receive_request(
        self, presentation_exchange_record: V10PresentationExchange
    ):
        """
        Receive a presentation request.

        Args:
            presentation_exchange_record: presentation exchange record with
                request to receive

        Returns:
            The presentation_exchange_record, updated

        """
        presentation_exchange_record.state = (
            V10PresentationExchange.STATE_REQUEST_RECEIVED
        )
        async with self._profile.session() as session:
            await presentation_exchange_record.save(
                session, reason="receive presentation request"
            )

        return presentation_exchange_record

    async def create_presentation(
        self,
        presentation_exchange_record: V10PresentationExchange,
        requested_credentials: dict,
        comment: str = None,
    ):
        """
        Create a presentation.

        Args:
            presentation_exchange_record: Record to update
            requested_credentials: Indy formatted requested_credentials
            comment: optional human-readable comment


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
        indy_handler = IndyPresExchHandler(self._profile)
        indy_proof = await indy_handler.return_presentation(
            pres_ex_record=presentation_exchange_record,
            requested_credentials=requested_credentials,
        )

        presentation_message = Presentation(
            comment=comment,
            presentations_attach=[
                AttachDecorator.data_base64(
                    mapping=indy_proof, ident=ATTACH_DECO_IDS[PRESENTATION]
                )
            ],
        )

        # Assign thid (and optionally pthid) to message
        presentation_message.assign_thread_from(
            presentation_exchange_record.presentation_request_dict
        )
        presentation_message.assign_trace_decorator(
            self._profile.settings, presentation_exchange_record.trace
        )

        # save presentation exchange state
        presentation_exchange_record.state = (
            V10PresentationExchange.STATE_PRESENTATION_SENT
        )
        presentation_exchange_record.presentation = indy_proof
        async with self._profile.session() as session:
            await presentation_exchange_record.save(
                session, reason="create presentation"
            )

        return presentation_exchange_record, presentation_message

    async def receive_presentation(
        self,
        message: Presentation,
        connection_record: Optional[ConnRecord],
        oob_record: Optional[OobRecord],
    ):
        """
        Receive a presentation, from message in context on manager creation.

        Returns:
            presentation exchange record, retrieved and updated

        """
        presentation = message.indy_proof()

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
            # Find by thread_id and role. Verify connection id later
            presentation_exchange_record = (
                await V10PresentationExchange.retrieve_by_tag_filter(
                    session,
                    {"thread_id": thread_id},
                    {
                        "role": V10PresentationExchange.ROLE_VERIFIER,
                        "connection_id": connection_id,
                    },
                )
            )

        # Save connection id (if it wasn't already present)
        if connection_record:
            presentation_exchange_record.connection_id = connection_record.connection_id

        # Check for bait-and-switch in presented attribute values vs. proposal
        if presentation_exchange_record.presentation_proposal_dict:
            exchange_pres_proposal = (
                presentation_exchange_record.presentation_proposal_dict
            )
            presentation_preview = exchange_pres_proposal.presentation_proposal

            proof_req = presentation_exchange_record._presentation_request.ser
            for reft, attr_spec in presentation["requested_proof"][
                "revealed_attrs"
            ].items():
                name = proof_req["requested_attributes"][reft]["name"]
                value = attr_spec["raw"]
                if not presentation_preview.has_attr_spec(
                    cred_def_id=presentation["identifiers"][
                        attr_spec["sub_proof_index"]
                    ]["cred_def_id"],
                    name=name,
                    value=value,
                ):
                    presentation_exchange_record.state = (
                        V10PresentationExchange.STATE_ABANDONED
                    )
                    async with self._profile.session() as session:
                        await presentation_exchange_record.save(
                            session,
                            reason=(
                                f"Presentation {name}={value} mismatches proposal value"
                            ),
                        )
                    raise PresentationManagerError(
                        f"Presentation {name}={value} mismatches proposal value"
                    )

        presentation_exchange_record.presentation = presentation
        presentation_exchange_record.state = (
            V10PresentationExchange.STATE_PRESENTATION_RECEIVED
        )

        async with self._profile.session() as session:
            await presentation_exchange_record.save(
                session, reason="receive presentation"
            )

        return presentation_exchange_record

    async def verify_presentation(
        self,
        presentation_exchange_record: V10PresentationExchange,
        responder: Optional[BaseResponder] = None,
    ):
        """
        Verify a presentation.

        Args:
            presentation_exchange_record: presentation exchange record
                with presentation request and presentation to verify

        Returns:
            presentation record, updated

        """
        indy_proof_request = presentation_exchange_record._presentation_request.ser
        indy_proof = presentation_exchange_record._presentation.ser
        indy_handler = IndyPresExchHandler(self._profile)
        (
            schemas,
            cred_defs,
            rev_reg_defs,
            rev_reg_entries,
        ) = await indy_handler.process_pres_identifiers(indy_proof["identifiers"])

        verifier = self._profile.inject(IndyVerifier)
        (verified_bool, verified_msgs) = await verifier.verify_presentation(
            dict(
                indy_proof_request
            ),  # copy to avoid changing the proof req in the stored pres exch
            indy_proof,
            schemas,
            cred_defs,
            rev_reg_defs,
            rev_reg_entries,
        )
        presentation_exchange_record.verified = json.dumps(verified_bool)
        presentation_exchange_record.verified_msgs = list(set(verified_msgs))
        presentation_exchange_record.state = V10PresentationExchange.STATE_VERIFIED

        async with self._profile.session() as session:
            await presentation_exchange_record.save(
                session, reason="verify presentation"
            )

        await self.send_presentation_ack(presentation_exchange_record, responder)
        return presentation_exchange_record

    async def send_presentation_ack(
        self,
        presentation_exchange_record: V10PresentationExchange,
        responder: Optional[BaseResponder] = None,
    ):
        """
        Send acknowledgement of presentation receipt.

        Args:
            presentation_exchange_record: presentation exchange record with thread id

        """
        responder = responder or self._profile.inject_or(BaseResponder)

        if not presentation_exchange_record.connection_id:
            # Find associated oob record. If this presentation exchange is created
            # without oob (aip1 style connectionless) we can't send a presentation ack
            # because we don't have their service
            try:
                async with self._profile.session() as session:
                    await OobRecord.retrieve_by_tag_filter(
                        session,
                        {"attach_thread_id": presentation_exchange_record.thread_id},
                    )
            except StorageNotFoundError:
                # This can happen in AIP1 style connectionless exchange. ACA-PY only
                # supported this for receiving a presentation
                LOGGER.error(
                    "Unable to send connectionless presentation ack without associated "
                    "oob record. This can happen if proof request was sent without "
                    "wrapping it in an out of band invitation (AIP1-style)."
                )
                return

        if responder:
            presentation_ack_message = PresentationAck(
                verification_result=presentation_exchange_record.verified
            )
            presentation_ack_message._thread = {
                "thid": presentation_exchange_record.thread_id
            }
            presentation_ack_message.assign_trace_decorator(
                self._profile.settings, presentation_exchange_record.trace
            )

            await responder.send_reply(
                presentation_ack_message,
                # connection_id can be none in case of connectionless
                connection_id=presentation_exchange_record.connection_id,
            )

            # all done: delete
            if presentation_exchange_record.auto_remove:
                async with self._profile.session() as session:
                    await presentation_exchange_record.delete_record(session)
        else:
            LOGGER.warning(
                "Configuration has no BaseResponder: cannot ack presentation on %s",
                presentation_exchange_record.thread_id,
            )

    async def receive_presentation_ack(
        self, message: PresentationAck, connection_record: Optional[ConnRecord]
    ):
        """
        Receive a presentation ack, from message in context on manager creation.

        Returns:
            presentation exchange record, retrieved and updated

        """
        connection_id = connection_record.connection_id if connection_record else None

        async with self._profile.session() as session:
            (
                presentation_exchange_record
            ) = await V10PresentationExchange.retrieve_by_tag_filter(
                session,
                {"thread_id": message._thread_id},
                {
                    # connection_id can be null in connectionless
                    "connection_id": connection_id,
                    "role": V10PresentationExchange.ROLE_PROVER,
                },
            )
            presentation_exchange_record.verified = message._verification_result
            presentation_exchange_record.state = (
                V10PresentationExchange.STATE_PRESENTATION_ACKED
            )

            await presentation_exchange_record.save(
                session, reason="receive presentation ack"
            )

            # all done: delete
            if presentation_exchange_record.auto_remove:
                async with self._profile.session() as session:
                    await presentation_exchange_record.delete_record(session)

        return presentation_exchange_record

    async def receive_problem_report(
        self, message: PresentationProblemReport, connection_id: str
    ):
        """
        Receive problem report.

        Returns:
            presentation exchange record, retrieved and updated

        """
        # FIXME use transaction, fetch for_update
        async with self._profile.session() as session:
            pres_ex_record = await V10PresentationExchange.retrieve_by_tag_filter(
                session,
                {"thread_id": message._thread_id},
                {"connection_id": connection_id},
            )

            pres_ex_record.state = V10PresentationExchange.STATE_ABANDONED
            code = message.description.get("code", ProblemReportReason.ABANDONED.value)
            pres_ex_record.error_msg = f"{code}: {message.description.get('en', code)}"
            await pres_ex_record.save(session, reason="received problem report")

        return pres_ex_record
