"""Introduction service demo classes."""

import json
import logging

from ...connections.models.connection_record import ConnectionRecord
from ...storage.base import BaseStorage, StorageRecord, StorageNotFoundError

from .base_service import BaseIntroductionService, IntroductionError
from .messages.forward_invitation import ForwardInvitation
from .messages.invitation import Invitation
from .messages.invitation_request import InvitationRequest

LOGGER = logging.getLogger(__name__)


class DemoIntroductionService(BaseIntroductionService):
    """Service handler for allowing connections to exchange invitations."""

    RECORD_TYPE = "introduction_record"

    async def start_introduction(
        self,
        init_connection_id: str,
        target_connection_id: str,
        message: str,
        outbound_handler,
    ):
        """
        Start the introduction process between two connections.

        Args:
            init_connection_id: The connection initiating the request
            target_connection_id: The connection which is asked for an invitation
            outbound_handler: The outbound handler coroutine for sending a message
            message: The message to use when requesting the invitation
        """

        try:
            init_connection = await ConnectionRecord.retrieve_by_id(
                self._context, init_connection_id
            )
        except StorageNotFoundError:
            raise IntroductionError("Initiator connection not found")

        if init_connection.state != "active":
            raise IntroductionError("Initiator connection is not active")

        try:
            target_connection = await ConnectionRecord.retrieve_by_id(
                self._context, target_connection_id
            )
        except StorageNotFoundError:
            raise IntroductionError("Target connection not found")

        if target_connection.state != "active":
            raise IntroductionError("Target connection is not active")

        msg = InvitationRequest(responder=init_connection.their_label, message=message)

        record = StorageRecord(
            type=self.RECORD_TYPE,
            value=json.dumps({"thread_id": msg._id, "state": "pending"}),
            tags={
                "init_connection_id": init_connection_id,
                "target_connection_id": target_connection_id,
            },
        )
        storage: BaseStorage = await self._context.inject(BaseStorage)
        await storage.add_record(record)

        await outbound_handler(msg, connection_id=target_connection_id)

    async def return_invitation(
        self, target_connection_id: str, invitation: Invitation, outbound_handler
    ):
        """
        Handle the forwarding of an invitation to the responder.

        Args:
            target_connection_id: The ID of the connection sending the Invitation
            invitation: The received Invitation message
            outbound_handler: The outbound handler coroutine for sending a message
        """

        thread_id = invitation._thread_id

        tag_filter = {"target_connection_id": target_connection_id}
        storage: BaseStorage = await self._context.inject(BaseStorage)
        records = await storage.search_records(self.RECORD_TYPE, tag_filter).fetch_all()

        found = False
        for row in records:
            value = json.loads(row.value)
            if value["thread_id"] == thread_id and value["state"] == "pending":
                msg = ForwardInvitation(
                    invitation=invitation.invitation, message=invitation.message
                )
                msg.assign_thread_from(invitation)

                value["state"] = "complete"
                await storage.update_record_value(row, json.dumps(value))

                init_connection_id = row.tags["init_connection_id"]
                await outbound_handler(msg, connection_id=init_connection_id)
                found = True
                LOGGER.info("Forwarded invitation to %s", init_connection_id)
                break

        if not found:
            LOGGER.error("Could not forward invitation, no pending introduction found")
