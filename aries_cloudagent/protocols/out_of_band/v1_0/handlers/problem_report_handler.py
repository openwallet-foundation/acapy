"""OOB Problem Report Message Handler."""

import logging

from .....config.logging import get_logger_inst
from .....messaging.base_handler import BaseHandler
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder

from ..manager import OutOfBandManager, OutOfBandManagerError
from ..messages.problem_report import OOBProblemReport


class OOBProblemReportMessageHandler(BaseHandler):
    """Handler class for OOB Problem Report Message.

    Updates the ConnRecord Metadata state.
    """

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """OOB Problem Report Message Handler.

        Args:
            context: Request context
            responder: Responder callback
        """
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug(f"OOBProblemReportMessageHandler called with context {context}")
        assert isinstance(context.message, OOBProblemReport)

        profile = context.profile
        mgr = OutOfBandManager(profile)
        try:
            await mgr.receive_problem_report(
                problem_report=context.message,
                receipt=context.message_receipt,
                conn_record=context.connection_record,
            )
        except OutOfBandManagerError:
            _logger.exception("Error processing OOB Problem Report message")
