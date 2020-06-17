"""Classes to manage connections."""

import logging

from typing import Tuple

from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.error import BaseError
from aries_cloudagent.wallet.base import BaseWallet
from aries_cloudagent.ledger.base import BaseLedger

from .models.invitation import Invitation as InvitationModel
from .messages.invitation import Invitation as InvitationMessage
from .messages.service import Service as ServiceMessage

from aries_cloudagent.protocols.connections.v1_0.manager import ConnectionManager

from aries_cloudagent.protocols.issue_credential.v1_0.models.credential_exchange import (
    V10CredentialExchange,
)

from aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange import (
    V10PresentationExchange,
)


class OutOfBandManagerError(BaseError):
    """Out of band error."""


class OutOfBandManager:
    """Class for managing out of band messages."""

    def __init__(self, context: InjectionContext):
        """
        Initialize a OutOfBandManager.

        Args:
            context: The context for this out of band manager
        """
        self._context = context
        self._logger = logging.getLogger(__name__)

    @property
    def context(self) -> InjectionContext:
        """
        Accessor for the current injection context.

        Returns:
            The injection context for this connection manager

        """
        return self._context

    async def create_invitation(
        self,
        my_label: str = None,
        my_endpoint: str = None,
        use_public_did: bool = False,
        include_handshake: bool = False,
        multi_use: bool = False,
        attachments: list = None,
    ) -> Tuple[InvitationModel, InvitationMessage]:
        """
        Generate new out of band invitation.

        This interaction represents an out-of-band communication channel. The resulting
        message is expected to be used to bootstrap the secure peer-to-peer communication
        channel.

        Args:
            my_label: label for this connection
            my_endpoint: endpoint where other party can reach me
            public: set to create an invitation from the public DID
            multi_use: set to True to create an invitation for multiple use
            attachments: list of dicts in the form of
                {"id": "jh5k23j5gh2123", "type": "credential-offer"}

        Returns:
            A tuple of the new `InvitationModel` and out of band `InvitationMessage`
            instances

        """

        connection_mgr = ConnectionManager(self.context)
        connection, connection_invitation = await connection_mgr.create_invitation(
            auto_accept=True, public=use_public_did, multi_use=multi_use
        )

        # wallet: BaseWallet = await self.context.inject(BaseWallet)

        if not my_label:
            my_label = self.context.settings.get("default_label")
        if not my_endpoint:
            my_endpoint = self.context.settings.get("default_endpoint")

        message_attachments = []
        if attachments:
            for attachment in attachments:
                if attachment["type"] == "credential-offer":
                    instance_id = attachment["id"]
                    model = await V10CredentialExchange.retrieve_by_id(
                        self.context, instance_id
                    )
                    # Wrap as attachment decorators
                    message_attachments.append(
                        InvitationMessage.wrap_message(model.credential_offer_dict)
                    )
                if attachment["type"] == "present-proof":
                    instance_id = attachment["id"]
                    model = await V10PresentationExchange.retrieve_by_id(
                        self.context, instance_id
                    )
                    # Wrap as attachment decorators
                    message_attachments.append(
                        InvitationMessage.wrap_message(model.presentation_request_dict)
                    )

        if use_public_did:
            # service = (await wallet.get_public_did()).did
            service = connection_invitation.did
        else:
            # connection_key = await wallet.create_signing_key()
            # service = ServiceMessage(
            #     id="#inline",
            #     type="did-communication",
            #     recipient_keys=[connection_key.verkey],
            #     routing_keys=[],
            #     service_endpoint=my_endpoint,
            # )
            service = ServiceMessage(
                id="#inline",
                type="did-communication",
                recipient_keys=connection_invitation.recipient_keys,
                routing_keys=connection_invitation.routing_keys,
                service_endpoint=connection_invitation.endpoint,
            )

        handshake_protocols = []
        if include_handshake:
            handshake_protocols.append("https://didcomm.org/connections/1.0")
            # handshake_protocols.append("https://didcomm.org/didexchange/1.0")

        invitation_message = InvitationMessage(
            label=my_label,
            service=[service],
            request_attach=message_attachments,
            handshake_protocols=handshake_protocols,
        )

        # Create record
        invitation_model = InvitationModel(
            state=InvitationModel.STATE_INITIAL,
            invitation=invitation_message.serialize(),
        )

        await invitation_model.save(self.context, reason="Created new invitation")

        return invitation_model

    async def receive_invitation(
        self, invitation: InvitationMessage
    ) -> Tuple[InvitationModel, InvitationMessage]:
        """
        Receive an out of band invitation message.
        """

        ledger: BaseLedger = await self.context.inject(BaseLedger)

        invitation_message = InvitationMessage.deserialize(invitation)

        


        services = []
        for service in invitation["service"]:
            # If service is a string, assume it is a valid did
            if type(service) is str:
                verkey = await ledger.get_key_for_did(service)
                endpoint = await ledger.get_endpoint_for_did(service)
                service = ServiceMessage(
                    id="#inline",
                    type="did-communication",
                    recipient_keys=[verkey],
                    routing_keys=[],
                    service_endpoint=endpoint,
                )
                services.append(service)
            # If service is a dict, assume it is a valid Service decorator
            elif type(service) is dict:
                service = ServiceMessage.deserialize(service)
                service.append(service)
            else:
                raise OutOfBandManager(
                    f"Item in service list is not str or dict, it is {type(service)}"
                )


        # Iterate over handshake protocols if exists

        # Try to resolve each protocol type and form connection
        # Break after first connection formed in order

        # If handshake protocols not empty and no connection formed, raise exception

        # Iterate of request attach and try to process each entity
        # If handshake protocols not empty, use previously formed connection
        # If empty, use ephemeral
