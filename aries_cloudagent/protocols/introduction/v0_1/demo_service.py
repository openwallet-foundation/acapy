"""Introduction service demo classes."""

import json
import logging

from ....connections.models.conn_record import ConnRecord
from ....core.profile import ProfileSession
from ....storage.base import (
    BaseStorage,
    StorageRecord,
    StorageNotFoundError,
)

from .base_service import BaseIntroductionService, IntroductionError
from .messages.forward_invitation import ForwardInvitation
from .messages.invitation import Invitation as IntroInvitation
from .messages.invitation_request import InvitationRequest as IntroInvitationRequest

LOGGER = logging.getLogger(__name__)


class DemoIntroductionService(BaseIntroductionService):
    """Service handler for allowing connections to exchange invitations."""

    RECORD_TYPE = "introduction_record"

    async def start_introduction(
        self,
        init_connection_id: str,
        target_connection_id: str,
        message: str,
        session: ProfileSession,
        outbound_handler,
    ):
        """
        Start the introduction process between two connections.

        Args:
            init_connection_id: The connection initiating the request
            target_connection_id: The connection which is asked for an invitation
            outbound_handler: The outbound handler coroutine for sending a message
            session: Profile session to use for connection, introduction records
            message: The message to use when requesting the invitation
        """
        try:
            init_connection = await ConnRecord.retrieve_by_id(
                session, init_connection_id
            )
        except StorageNotFoundError:
            raise IntroductionError(
                f"Initiator connection {init_connection_id} not found"
            )

        if (
            ConnRecord.State.get(init_connection.state)
            is not ConnRecord.State.COMPLETED
        ):
            raise IntroductionError(
                f"Initiator connection {init_connection_id} not active"
            )

        try:
            target_connection = await ConnRecord.retrieve_by_id(
                session, target_connection_id
            )
        except StorageNotFoundError:
            raise IntroductionError(
                "Target connection {target_connection_id} not found"
            )

        if (
            ConnRecord.State.get(target_connection.state)
            is not ConnRecord.State.COMPLETED
        ):
            raise IntroductionError(
                "Target connection {target_connection_id} not active"
            )

        msg = IntroInvitationRequest(
            responder=init_connection.their_label,
            message=message,
        )

        record = StorageRecord(
            type=DemoIntroductionService.RECORD_TYPE,
            value=json.dumps({"thread_id": msg._id, "state": "pending"}),
            tags={
                "init_connection_id": init_connection_id,
                "target_connection_id": target_connection_id,
            },
        )

        storage = session.inject(BaseStorage)
        await storage.add_record(record)

        await outbound_handler(msg, connection_id=target_connection_id)

    async def return_invitation(
        self,
        target_connection_id: str,
        invitation: IntroInvitation,
        session: ProfileSession,
        outbound_handler,
    ):
        """
        Handle the forwarding of an invitation to the responder.

        Args:
            target_connection_id: The ID of the connection sending the Invitation
            invitation: The received (Introduction) Invitation message
            session: Profile session to use for introduction records
            outbound_handler: The outbound handler coroutine for sending a message
        """
        thread_id = invitation._thread_id

        tag_filter = {"target_connection_id": target_connection_id}
        storage = session.inject(BaseStorage)
        records = await storage.find_all_records(
            DemoIntroductionService.RECORD_TYPE,
            tag_filter,
        )

        found = False
        for row in records:
            value = json.loads(row.value)
            if value["thread_id"] == thread_id and value["state"] == "pending":
                msg = ForwardInvitation(
                    invitation=invitation.invitation, message=invitation.message
                )
                msg.assign_thread_from(invitation)
                msg.assign_trace_from(invitation)

                value["state"] = "complete"
                await storage.update_record(row, json.dumps(value), row.tags)

                init_connection_id = row.tags["init_connection_id"]
                await outbound_handler(msg, connection_id=init_connection_id)
                found = True
                LOGGER.info("Forwarded fwd-invitation to %s", init_connection_id)
                break

        if not found:
            LOGGER.error("Could not forward invitation, no pending introduction found")
