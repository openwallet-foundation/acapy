"""Handler for mediate-deny message."""

from .....config.logging import get_adapted_logger_inst
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
        profile = context.profile
        self._logger = get_adapted_logger_inst(
            logger=self._logger,
            log_file=profile.settings.get("log.file"),
            wallet_id=profile.settings.get("wallet.id"),
        )
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, MediationDeny)

        if not context.connection_ready:
            raise HandlerException("Received mediation deny from inactive connection")
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
