"""Handler for keylist message."""
import logging

from .....config.logging import get_logger_inst
from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageNotFoundError

from ..messages.keylist import Keylist
from ..models.mediation_record import MediationRecord


class KeylistHandler(BaseHandler):
    """Handler for keylist message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle keylist message."""
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug("%s called with context %s", self.__class__.__name__, context)
        assert isinstance(context.message, Keylist)

        if not context.connection_ready:
            raise HandlerException("Received keylist message from inactive connection")

        try:
            async with context.profile.session() as session:
                await MediationRecord.retrieve_by_connection_id(
                    session, context.connection_record.connection_id
                )
        except StorageNotFoundError as err:
            _logger.warning(
                "Received keylist from connection that is not acting as mediator: %s",
                err,
            )
            return

        # TODO verify our keylist matches?
        _logger.info("Keylist received: %s", context.message)
