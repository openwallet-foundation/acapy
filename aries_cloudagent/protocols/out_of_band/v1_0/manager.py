"""Classes to manage connections."""

import logging


from typing import Sequence, Tuple


from aries_cloudagent.cache.base import BaseCache
from aries_cloudagent.connections.models.connection_record import ConnectionRecord

from aries_cloudagent.connections.models.connection_target import ConnectionTarget
from aries_cloudagent.connections.models.diddoc import (
    DIDDoc,
    PublicKey,
    PublicKeyType,
    Service,
)
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.error import BaseError
from aries_cloudagent.wallet.base import BaseWallet

# FIXME: We shouldn't rely on a hardcoded message version here.
from aries_cloudagent.protocols.routing.v1_0.manager import RoutingManager

from .messages.invitation import Invitation


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
        self, my_label: str = None, my_endpoint: str = None, multi_use: bool = False,
    ) -> Tuple[ConnectionRecord, Invitation]:
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

        Returns:
            A tuple of the new `ConnectionRecord` and out of band `Invitation` instances

        """
        if not my_label:
            my_label = self.context.settings.get("default_label")
        wallet: BaseWallet = await self.context.inject(BaseWallet)

        if multi_use:
            invitation_mode = ConnectionRecord.INVITATION_MODE_MULTI
        else:
            invitation_mode = ConnectionRecord.INVITATION_MODE_ONCE

        if not my_endpoint:
            my_endpoint = self.context.settings.get("default_endpoint")

        # Create and store new invitation key
        connection_key = await wallet.create_signing_key()

        # Create connection record
        connection = ConnectionRecord(
            initiator=ConnectionRecord.INITIATOR_SELF,
            invitation_key=connection_key.verkey,
            state=ConnectionRecord.STATE_INVITATION,
            invitation_mode=invitation_mode,
        )

        await connection.save(self.context, reason="Created new invitation")

        invitation = Invitation(
            label=my_label, recipient_keys=[connection_key.verkey], endpoint=my_endpoint
        )
        await connection.attach_invitation(self.context, invitation)

        return connection, invitation
