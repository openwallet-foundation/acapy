"""Oob message processor and functions."""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from ..connections.models.conn_record import ConnRecord
from ..connections.models.connection_target import ConnectionTarget
from ..messaging.agent_message import AgentMessage
from ..messaging.decorators.service_decorator import ServiceDecorator
from ..messaging.request_context import RequestContext
from ..protocols.didcomm_prefix import DIDCommPrefix
from ..protocols.didexchange.v1_0.message_types import ARIES_PROTOCOL as DIDEX_1_1
from ..protocols.didexchange.v1_0.message_types import DIDEX_1_0
from ..protocols.issue_credential.v2_0.message_types import CRED_20_OFFER
from ..protocols.out_of_band.v1_0.message_types import MESSAGE_REUSE
from ..protocols.out_of_band.v1_0.models.oob_record import OobRecord
from ..protocols.present_proof.v2_0.message_types import PRES_20_REQUEST
from ..storage.error import StorageDuplicateError, StorageNotFoundError
from ..transport.inbound.message import InboundMessage
from ..transport.outbound.message import OutboundMessage
from ..transport.wire_format import JsonWireFormat
from .error import BaseError
from .profile import Profile

LOGGER = logging.getLogger(__name__)

# Message types that, per the OOB/DID-exchange protocols, are always sent by the
# *receiver* of an invitation back to the *sender* (e.g. a connection request in
# response to a handshake, or a request to reuse an existing connection). These are
# processed by the party holding the role=sender OobRecord for the invitation.
_SENDER_ROLE_MESSAGE_TYPES = {
    f"{DIDEX_1_0}/request",
    f"{DIDEX_1_1}/request",
    MESSAGE_REUSE,
}


class OobMessageProcessorError(BaseError):
    """Base error for OobMessageProcessor."""


class OobMessageProcessor:
    """Out of band message processor."""

    def __init__(
        self,
        inbound_message_router: Callable[[Profile, InboundMessage, Optional[bool]], None],
    ) -> None:
        """Initialize an inbound OOB message processor.

        Args:
            inbound_message_router: Method to create a new inbound session

        """
        self._inbound_message_router = inbound_message_router
        self.wire_format = JsonWireFormat()

    async def clean_finished_oob_record(self, profile: Profile, message: AgentMessage):
        """Clean up oob record associated with agent message, if applicable."""
        try:
            async with profile.session() as session:
                oob_record = await OobRecord.retrieve_by_tag_filter(
                    session,
                    {"invi_msg_id": message._thread.pthid},
                    {"role": OobRecord.ROLE_SENDER},
                )

                # emit the "done" event for OOB invitations
                if not oob_record.invitation.requests_attach:
                    oob_record.state = OobRecord.STATE_DONE
                    await oob_record.emit_event(session)

                # If the oob record is not multi use and it doesn't contain any
                # attachments, we can now safely remove the oob record
                if not oob_record.multi_use and not oob_record.invitation.requests_attach:
                    await oob_record.delete_record(session)
        except StorageNotFoundError:
            # It is fine if no oob record is found, Only retrieved for cleanup
            pass
        except Exception:
            LOGGER.warning("Error cleaning up oob record", exc_info=True)

    async def find_oob_target_for_outbound_message(
        self, profile: Profile, outbound_message: OutboundMessage
    ) -> Optional[ConnectionTarget]:
        """Find connection target for the outbound message."""
        try:
            async with profile.session() as session:
                # Try to find the oob record for the outbound message:
                oob_record = await OobRecord.retrieve_by_tag_filter(
                    session, {"attach_thread_id": outbound_message.reply_thread_id}
                )

                LOGGER.debug(
                    "extracting their service from oob record %s",
                    oob_record.their_service,
                )

                their_service = oob_record.their_service
                if not their_service:
                    raise OobMessageProcessorError("Could not determine their service")

                # Attach ~service decorator so other message can respond
                message = json.loads(outbound_message.payload)
                if not message.get("~service") and oob_record.our_service:
                    LOGGER.debug(
                        "Setting our service on the message ~service %s",
                        oob_record.our_service,
                    )
                    message["~service"] = oob_record.our_service.serialize()

                message["~thread"] = {
                    **message.get("~thread", {}),
                    "pthid": oob_record.invi_msg_id,
                }

                outbound_message.payload = json.dumps(message)

                LOGGER.debug("Sending oob message payload %s", outbound_message.payload)

                return ConnectionTarget(
                    endpoint=their_service.endpoint,
                    recipient_keys=their_service.recipient_keys,
                    routing_keys=their_service.routing_keys,
                    sender_key=oob_record.our_recipient_key,
                )
        except StorageNotFoundError:
            return None

    async def find_oob_record_for_inbound_message(
        self, context: RequestContext
    ) -> Optional[OobRecord]:
        """Find oob record for inbound message."""
        message_type = context.message._type
        oob_record = None
        async with context.profile.session() as session:
            # First try to find the oob record based on the associated pthid
            if context.message_receipt.parent_thread_id:
                try:
                    LOGGER.debug(
                        "Retrieving OOB record using pthid "
                        f"{context.message_receipt.parent_thread_id} "
                        f"for message type {message_type}"
                    )
                    oob_record = await OobRecord.retrieve_by_tag_filter(
                        session,
                        {"invi_msg_id": context.message_receipt.parent_thread_id},
                    )
                except StorageNotFoundError:
                    # Fine if record is not found
                    pass
                except StorageDuplicateError:
                    # Multiple oob records share this invi_msg_id. This happens when
                    # an agent creates an OOB invitation and then receives that same
                    # invitation back into the same wallet (e.g. self-issuance): one
                    # OobRecord has role=sender (from create-invitation) and another
                    # has role=receiver (from receive-invitation).
                    #
                    # Disambiguate primarily using the recipient verkey the inbound
                    # message was actually delivered to: each side of a connectionless
                    # exchange uses its own key (OobRecord.our_recipient_key), so the
                    # recipient_verkey on the envelope tells us unambiguously which of
                    # the two records this message belongs to, regardless of protocol
                    # or message type (credential offers/requests, presentation
                    # requests/presentations/acks, did-exchange requests, handshake
                    # reuse, ...).
                    if context.message_receipt.recipient_verkey:
                        try:
                            oob_record = await OobRecord.retrieve_by_tag_filter(
                                session,
                                {
                                    "invi_msg_id": (
                                        context.message_receipt.parent_thread_id
                                    ),
                                    "our_recipient_key": (
                                        context.message_receipt.recipient_verkey
                                    ),
                                },
                            )
                            LOGGER.debug(
                                "Multiple OOB records found for invi_msg_id %s; "
                                "disambiguated using recipient verkey %s to oob "
                                "record %s",
                                context.message_receipt.parent_thread_id,
                                context.message_receipt.recipient_verkey,
                                oob_record.oob_id,
                            )
                        except (StorageNotFoundError, StorageDuplicateError):
                            # Fine if record is not found (or, unexpectedly, still
                            # ambiguous); fall back to the message-type heuristic
                            oob_record = None

                    # Fall back to disambiguating by message type. This is needed
                    # when the message was delivered without going through the wire
                    # format (e.g. the initial oob attachment message, which is
                    # handled locally and therefore has no recipient_verkey). Some
                    # message types are always sent by the receiver of an invitation
                    # back to the sender, so we must be looking for our role=sender
                    # record to process them; all other message types (e.g. attached
                    # protocol messages like credential offers) are sent by the
                    # sender to the receiver, so we must be looking for our
                    # role=receiver record.
                    if not oob_record:
                        expected_role = (
                            OobRecord.ROLE_SENDER
                            if DIDCommPrefix.unqualify(message_type)
                            in _SENDER_ROLE_MESSAGE_TYPES
                            else OobRecord.ROLE_RECEIVER
                        )
                        LOGGER.debug(
                            "Multiple OOB records found for invi_msg_id %s; "
                            "disambiguating using role %s for message type %s",
                            context.message_receipt.parent_thread_id,
                            expected_role,
                            message_type,
                        )
                        try:
                            oob_record = await OobRecord.retrieve_by_tag_filter(
                                session,
                                {
                                    "invi_msg_id": (
                                        context.message_receipt.parent_thread_id
                                    )
                                },
                                {"role": expected_role},
                            )
                        except StorageNotFoundError:
                            # Fine if record is not found
                            pass
            # Otherwise try to find it using the attach thread id. This is only needed
            # for connectionless exchanges where every handler needs the context of the
            # oob record for verification. We could attach the oob_record to all messages,
            # even if we have a connection, but it would add another query to all inbound
            # messages.
            if (
                not oob_record
                and not context.connection_record
                and context.message_receipt.thread_id
                and context.message_receipt.recipient_verkey
            ):
                try:
                    LOGGER.debug(
                        "Retrieving OOB record using thid "
                        f"{context.message_receipt.thread_id} and recipient verkey"
                        f" {context.message_receipt.recipient_verkey} for "
                        f"message type {message_type}"
                    )
                    oob_record = await OobRecord.retrieve_by_tag_filter(
                        session,
                        {
                            "attach_thread_id": context.message_receipt.thread_id,
                            "our_recipient_key": context.message_receipt.recipient_verkey,
                        },
                    )
                except StorageNotFoundError:
                    # Fine if record is not found
                    pass

        # If not oob record was found we can return early without oob record
        if not oob_record:
            return None

        LOGGER.debug(
            f"Found out of band record for inbound message with type {message_type}"
            f": {oob_record.oob_id}"
        )

        # If the connection does not match with the connection id associated with the
        # oob record we don't want to associate the oob record to the current context
        # This is not the case if the state is await response, in this case we might want
        # to update the connection id on the oob record
        if (
            # Only if we created the invitation
            oob_record.role == OobRecord.ROLE_SENDER
            # If connection is present and not same as oob_record conn id
            and context.connection_record
            and context.connection_record.connection_id != oob_record.connection_id
        ):
            LOGGER.debug(
                f"Oob record connection id {oob_record.connection_id} is different from"
                f" inbound message connection {context.connection_record.connection_id}",
            )
            # Mismatch in connection id's in only allowed in state await response
            # (connection id can change bc of reuse)
            if oob_record.state != OobRecord.STATE_AWAIT_RESPONSE:
                LOGGER.debug(
                    "Inbound message has incorrect connection_id "
                    f"{context.connection_record.connection_id}. Oob record "
                    f"{oob_record.oob_id} associated with connection id "
                    f"{oob_record.connection_id}"
                )
                return None

            # If the state is await response, and there are attachments we want to update
            # the connection id on the oob record. In case no request_attach is present,
            # this is handled by the reuse handlers
            if (
                oob_record.invitation.requests_attach
                and oob_record.state == OobRecord.STATE_AWAIT_RESPONSE
            ):
                # Remove stale connection due to connection reuse. But first check
                # whether the "old" connection is actually the mirror-image
                # ConnRecord of a self-connection: when an agent's own wallet plays
                # both the inviter and invitee roles for one invitation (e.g.
                # self-issuance), each role gets its own ConnRecord, and both DIDs
                # are reciprocal (old.my_did == new.their_did and vice versa). That
                # "old" record is not stale -- it is still awaiting its own
                # DIDXComplete -- so deleting it here causes accept_complete to
                # fail with "No corresponding connection request found".
                old_conn_record = None
                if oob_record.connection_id:
                    async with context.profile.session() as session:
                        try:
                            old_conn_record = await ConnRecord.retrieve_by_id(
                                session, oob_record.connection_id
                            )
                        except StorageNotFoundError:
                            old_conn_record = None

                is_self_connection_mirror = bool(
                    old_conn_record
                    and old_conn_record.my_did
                    and old_conn_record.their_did
                    and old_conn_record.my_did == context.connection_record.their_did
                    and old_conn_record.their_did == context.connection_record.my_did
                )

                if old_conn_record and not is_self_connection_mirror:
                    LOGGER.debug(
                        f"Removing stale connection {oob_record.connection_id} due "
                        "to connection reuse"
                    )
                    async with context.profile.session() as session:
                        await old_conn_record.delete_record(session)
                elif is_self_connection_mirror:
                    LOGGER.debug(
                        f"Not removing connection {oob_record.connection_id}: it is "
                        "the other role's own ConnRecord for this self-connection "
                        "and is still awaiting its own handshake completion"
                    )

                oob_record.connection_id = context.connection_record.connection_id

        # If no attach_thread_id is stored yet we need to match the current message
        # thread_id against the attached messages in the oob invitation
        if not oob_record.attach_thread_id and oob_record.invitation.requests_attach:
            # Check if the current message thread_id corresponds to one of the invitation
            # ~thread.thid
            allowed_thread_ids = [
                self.get_thread_id(attachment.content)
                for attachment in oob_record.invitation.requests_attach
            ]

            if context.message_receipt.thread_id not in allowed_thread_ids:
                LOGGER.debug(
                    "Inbound message is for not allowed thread "
                    f"{context.message_receipt.thread_id}. Allowed "
                    f"threads are {allowed_thread_ids}"
                )
                return None

            oob_record.attach_thread_id = context.message_receipt.thread_id
        elif (
            oob_record.attach_thread_id
            and context.message_receipt.thread_id != oob_record.attach_thread_id
        ):
            LOGGER.debug(
                f"Inbound message thread id {context.message_receipt.thread_id} does not"
                f" match oob record thread id {oob_record.attach_thread_id}"
            )
            return None

        # Verify the sender key is present in their service in our record
        # If we don't have the sender verkey stored yet we can allow any key
        if oob_record.their_service and (
            context.message_receipt.recipient_verkey
            and (
                not context.message_receipt.sender_verkey
                or context.message_receipt.sender_verkey
                not in oob_record.their_service.recipient_keys
            )
        ):
            LOGGER.debug(
                "Inbound message sender verkey does not match stored service on oob"
                " record"
            )
            return None

        # If the message has a ~service decorator we save it in the oob record so we
        # can reply to this message
        if context._message._service:
            LOGGER.debug(
                "Storing service decorator in oob record %s",
                context.message._service.serialize(),
            )
            oob_record.their_service = context.message._service.serialize()

        async with context.profile.session() as session:
            # We can now remove the oob record as the connection should now be stored in
            # the exchange record itself.
            if oob_record.connection_id:
                oob_record.state = OobRecord.STATE_DONE
                await oob_record.emit_event(session)
                await oob_record.delete_record(session)
            else:
                await oob_record.save(
                    session, reason="Update their service in oob record"
                )

        return oob_record

    async def handle_message(
        self,
        profile: Profile,
        messages: List[Dict[str, Any]],
        oob_record: OobRecord,
        their_service: Optional[ServiceDecorator] = None,
    ):
        """Message handler for inbound messages."""
        supported_types = [
            CRED_20_OFFER,
            PRES_20_REQUEST,
            "issue-credential/1.0/offer-credential",
            "present-proof/1.0/request-presentation",
        ]

        supported_messages = [
            message
            for message in messages
            if DIDCommPrefix.unqualify(message["@type"]) in supported_types
        ]

        if not supported_messages:
            message_str = ", ".join(supported_types)
            raise OobMessageProcessorError(
                f"None of the oob attached messages supported. Supported message types "
                f"are {message_str}"
            )

        message = supported_messages[0]
        message_str = json.dumps(message)

        async with profile.session() as session:
            message_dict, receipt = await self.wire_format.parse_message(
                session, message_str
            )

            inbound_message = InboundMessage(
                payload=message_dict,
                connection_id=oob_record.connection_id,
                receipt=receipt,
            )

            # We only need to store this data for connectionless
            # (it could be the oob record is already deleted)
            if not oob_record.connection_id:
                oob_record.attach_thread_id = self.get_thread_id(message)
                if their_service:
                    LOGGER.debug("Storing their service in oob record %s", their_service)
                    oob_record.their_service = their_service

                await oob_record.save(session)

        self._inbound_message_router(profile, inbound_message, False)

    def get_thread_id(self, message: Dict[str, Any]) -> str:
        """Extract thread id from agent message dict."""
        return message.get("~thread", {}).get("thid") or message.get("@id")
