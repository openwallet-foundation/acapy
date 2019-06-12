"""Classes to manage issuer registrations."""

import asyncio
import json
import logging

from indy_catalyst_agent.error import BaseError
from indy_catalyst_agent.cache.base import BaseCache
from indy_catalyst_agent.holder.base import BaseHolder
from indy_catalyst_agent.issuer.base import BaseIssuer
from indy_catalyst_agent.ledger.base import BaseLedger
from indy_catalyst_agent.models.thread_decorator import ThreadDecorator

from indy_catalyst_agent.messaging.connections.models.connection_record import (
    ConnectionRecord,
)
from indy_catalyst_agent.messaging.request_context import RequestContext

from .models.issuer_registration import IssuerRegistration

from indy_catalyst_agent.storage.error import StorageNotFoundError
from indy_catalyst_agent.messaging.util import send_webhook


class IssuerRegistrationManagerError(BaseError):
    """Issuer registration error."""


class IssuerRegistrationManager:
    """Class for managing issuer registrations."""

    def __init__(self, context: RequestContext):
        """
        Initialize a IssuerRegistrationManager.

        Args:
            context: The context for this issuer registration
        """
        self._context = context
        self._logger = logging.getLogger(__name__)

    @property
    def context(self) -> RequestContext:
        """
        Accessor for the current request context.

        Returns:
            The request context for this connection

        """
        return self._context

    async def prepare_send(self, connection_id, issuer_registration):
        """
        Create an issuer registration state object and agent messages.

        Args:
            connection_id: Connection to send the issuer registration to
            issuer_registration: The issuer registration payload

        Returns:
            A tuple (
                issuer_registration_state,
                issuer_registration_message
            )

        """

        credential_exchange = CredentialExchange(
            connection_id=connection_id,
            initiator=CredentialExchange.INITIATOR_SELF,
            issuer_registration=issuer_registration,
        )
