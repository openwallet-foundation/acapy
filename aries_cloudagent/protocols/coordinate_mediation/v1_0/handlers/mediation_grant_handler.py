"""Handler for mediate-grant message."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from .....storage.error import StorageNotFoundError
from ..manager import MediationManager
from ..messages.mediate_grant import MediationGrant
from ..models.mediation_record import MediationRecord


class MediationGrantHandler(BaseHandler):
    """Handler for mediate-grant message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle mediate-grant message."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, MediationGrant)

        if not context.connection_ready:
            raise HandlerException("Received mediation grant from inactive connection")

        session = await context.session()
        mgr = MediationManager(session)
        try:
            record = await MediationRecord.retrieve_by_connection_id(
                session, context.connection_record.connection_id
            )
            await mgr.request_granted(record, context.message)
        except StorageNotFoundError as err:
            raise HandlerException(
                "Received mediation grant from connection from which mediation "
                "has not been requested."
            ) from err
