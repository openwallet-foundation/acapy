"""Handler for mediate-deny message."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from .....storage.error import StorageNotFoundError
from ..manager import MediationManager
from ..messages.mediate_deny import MediationDeny
from ..models.mediation_record import MediationRecord


class MediationDenyHandler(BaseHandler):
    """Handler for mediate-deny message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle mediate-deny message."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, MediationDeny)

        if not context.connection_ready:
            raise HandlerException("Received mediation deny from inactive connection")

        mgr = MediationManager(context.profile)
        try:
            async with context.session() as session:
                record = await MediationRecord.retrieve_by_connection_id(
                    session, context.connection_record.connection_id
                )
            await mgr.request_denied(record, context.message)
        except StorageNotFoundError as err:
            raise HandlerException(
                "Received mediation grant from connection from which mediation "
                "has not been requested."
            ) from err
