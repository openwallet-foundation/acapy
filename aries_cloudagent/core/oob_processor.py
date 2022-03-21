"""Oob message processor and functions."""

import json
import logging
from typing import Any, Callable, Dict, List, Optional, cast

from ..messaging.agent_message import AgentMessage
from ..connections.models.conn_record import ConnRecord
from ..connections.models.connection_target import ConnectionTarget
from ..messaging.decorators.service_decorator import ServiceDecorator
from ..messaging.request_context import RequestContext
from ..protocols.didcomm_prefix import DIDCommPrefix
from ..protocols.issue_credential.v1_0.message_types import CREDENTIAL_OFFER
from ..protocols.issue_credential.v2_0.message_types import CRED_20_OFFER
from ..protocols.present_proof.v1_0.message_types import PRESENTATION_REQUEST
from ..protocols.present_proof.v2_0.message_types import PRES_20_REQUEST
from ..protocols.out_of_band.v1_0.models.oob_record import OobRecord
from ..storage.error import StorageNotFoundError
from ..transport.inbound.message import InboundMessage
from ..transport.outbound.message import OutboundMessage
from ..transport.wire_format import JsonWireFormat
from .profile import Profile

LOGGER = logging.getLogger(__name__)


class OobMessageProcessor:
    """Out of band message processor."""

    def __init__(
        self,
        inbound_message_router: Callable[
            [Profile, InboundMessage, Optional[bool]], None
        ],
    ) -> None:
        """
        Initialize an inbound OOB message processor

        Args:
            inbound_message_router: Method to create a new inbound session

        """
        self._inbound_message_router = inbound_message_router
        self.wire_format = JsonWireFormat()

    async def clean_finished_oob_record(self, profile: Profile, message: AgentMessage):
        try:
            async with profile.session() as session:
                oob_record = await OobRecord.retrieve_by_tag_filter(
                    session,
                    {"invi_msg_id": message._thread.pthid},
                    {"role": OobRecord.ROLE_SENDER},
                )

            # If the oob record is not multi use and it doesn't contain any attachments
            # We can now safely remove the oob record
            if not oob_record.multi_use and not oob_record.invitation.requests_attach:
                oob_record.state = OobRecord.STATE_DONE
                await oob_record.emit_event(session)
                await oob_record.delete_record(session)
        except Exception:
            # It is fine if no oob record is found, Only retrieved for cleanup
            pass

    async def find_oob_target_for_outbound_message(
        self, profile: Profile, outbound_message: OutboundMessage
    ) -> Optional[ConnectionTarget]:
        try:
            async with profile.session() as session:
                # Try to find the oob record for the outbound message:
                oob_record = await OobRecord.retrieve_by_tag_filter(
                    session, {"attach_thread_id": outbound_message.reply_thread_id}
                )

                their_service = oob_record.their_service
                their_service = ServiceDecorator.deserialize(their_service)

                # Attach ~service decorator so other message can respond
                message = json.loads(outbound_message.payload)
                if not message.get("~service"):
                    message["~service"] = oob_record.our_service.serialize()

                # OOB_TODO: state is somewhat done, but we need it for connectionless exchange
                # if is_first_response:
                message["~thread"] = {
                    **message.get("~thread", {}),
                    "pthid": oob_record.invi_msg_id,
                }

                outbound_message.payload = json.dumps(message)

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
        message_type = context.message._type
        oob_record = None

        async with context.profile.session() as session:
            # First try to find the oob record based on the associated pthid
            if context.message_receipt.parent_thread_id:
                try:
                    LOGGER.debug(
                        f"Retrieving OOB record using pthid {context.message_receipt.parent_thread_id} for message type {message_type}"
                    )
                    oob_record = await OobRecord.retrieve_by_tag_filter(
                        session,
                        {"invi_msg_id": context.message_receipt.parent_thread_id},
                    )
                except StorageNotFoundError:
                    # Fine if record is not found
                    pass
            # Otherwise try to find it using the attach thread id. This is only needed
            # for connectionless exchanges where every handlers needs the context of the oob
            # record for verification. We could attach the oob_record to all messages, even if
            # we have a connection, but it would add another query to all inbound messages.
            if (
                not oob_record
                and not context.connection_record
                and context.message_receipt.thread_id
                and context.message_receipt.recipient_verkey
            ):
                try:
                    LOGGER.debug(
                        f"Retrieving OOB record using thid {context.message_receipt.thread_id} and recipient verkey {context.message_receipt.recipient_verkey} for message type {message_type}"
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
            f"Found out of band record for inbound message with type {message_type}: %s",
            oob_record,
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
                f"Oob record connection id {oob_record.connection_id} is different from inbound message connection {context.connection_record.connection_id}",
            )
            # Mismatch in connection id's in only allowed in state await response (connection id can change bc of reuse)
            if oob_record.state != OobRecord.STATE_AWAIT_RESPONSE:
                LOGGER.debug(
                    f"Inbound message has incorrect connection_id {context.connection_record.connection_id}. Oob record {oob_record.oob_id} associated with connection id {oob_record.connection_id}"
                )
                return None

            # If the state is await response, and there are attachments we want to update the connection id
            # on the oob record. In case no request_attach is present, this is handled by the reuse handlers
            if (
                oob_record.invitation.requests_attach
                and oob_record.state == OobRecord.STATE_AWAIT_RESPONSE
            ):
                LOGGER.debug(
                    f"Removing stale connection {oob_record.connection_id} due to connection reuse"
                )
                # Remove stale connection due to connection reuse
                if oob_record.connection_id:
                    async with context.profile.session() as session:
                        old_conn_record = await ConnRecord.retrieve_by_id(
                            session, oob_record.connection_id
                        )
                        await old_conn_record.delete_record(session)

                oob_record.connection_id = context.connection_record.connection_id

        # If no attach_thread_id is stored yet we need to match the current message thread_id against the attached messages
        # in the oob invitation
        if not oob_record.attach_thread_id and oob_record.invitation.requests_attach:
            # Check if the current message thread_id corresponds to one of the invitation ~thread.thid
            allowed_thread_ids = [
                self.get_thread_id(attachment.content)
                for attachment in oob_record.invitation.requests_attach
            ]

            if not context.message_receipt.thread_id in allowed_thread_ids:
                LOGGER.debug(
                    f"Inbound message is for not allowed thread {context.message_receipt.thread_id}. Allowed threads are {allowed_thread_ids}"
                )
                return None

            oob_record.attach_thread_id = context.message_receipt.thread_id
        elif (
            oob_record.attach_thread_id
            and context.message_receipt.thread_id != oob_record.attach_thread_id
        ):
            LOGGER.debug(
                f"Inbound message thread id {context.message_receipt.thread_id} does not match oob record thread id {oob_record.attach_thread_id}"
            )
            return None

        their_service = (
            cast(
                ServiceDecorator,
                ServiceDecorator.deserialize(oob_record.their_service),
            )
            if oob_record.their_service
            else None
        )

        # Verify the sender key is present in their service in our record
        # If we don't have the sender verkey stored yet we can allow any key
        if their_service and (
            # We either want the sender key to be present and present in their_service
            (
                context.message_receipt.sender_verkey
                and context.message_receipt.sender_verkey
                not in their_service.recipient_keys
            )
            # Or we don't want the sender or recipient key to be present (in case of oob message handler)
            or (
                not context.message_receipt.sender_verkey
                and not context.message_receipt.recipient_verkey
            )
        ):
            LOGGER.debug(
                "Inbound message sender verkey does not match stored service on oob record"
            )
            return None

        # If the message has a ~service decorator we save it in the oob record so we can reply to this message
        if context._message._service:
            oob_record.their_service = context.message._service.serialize()

        async with context.profile.session() as session:
            # We can now remove the oob record as the connection should now be stored in the
            # exchange record itself.
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
        self, profile: Profile, messages: List[Dict[str, Any]], oob_record: OobRecord
    ):
        """Message handler for inbound messages."""

        supported_types = [
            CREDENTIAL_OFFER,
            CRED_20_OFFER,
            PRESENTATION_REQUEST,
            PRES_20_REQUEST,
        ]

        supported_messages = [
            message
            for message in messages
            if DIDCommPrefix.unqualify(message["@type"]) in supported_types
        ]

        if not supported_messages:
            raise Exception(
                f"None of the oob attached messages supported. Supported message types are {supported_types}"
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

        self._inbound_message_router(profile, inbound_message, False)

    def get_thread_id(self, message: Dict[str, Any]) -> str:
        return message.get("~thread", {}).get("thid") or message.get("@id")
