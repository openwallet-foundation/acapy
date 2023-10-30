"""Handler for mediate-deny message."""

from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
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

        profile = context.profile
        mgr = MediationManager(profile)
        try:
            async with profile.session() as session:
                record = await MediationRecord.retrieve_by_connection_id(
                    session, context.connection_record.connection_id
                )
            await mgr.request_denied(record, context.message)
        except StorageNotFoundError as err:
            raise HandlerException(
                "Received mediation grant from connection from which mediation "
                "has not been requested"
            ) from err
