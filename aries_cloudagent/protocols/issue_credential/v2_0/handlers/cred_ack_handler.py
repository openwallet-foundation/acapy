"""Credential ack message handler."""

import logging

from .....config.logging import get_logger_inst
from .....core.oob_processor import OobMessageProcessor
from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....utils.tracing import trace_event, get_timer

from ..manager import V20CredManager
from ..messages.cred_ack import V20CredAck


class V20CredAckHandler(BaseHandler):
    """Message handler class for credential acks."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler logic for credential acks.

        Args:
            context: request context
            responder: responder callback
        """
        r_time = get_timer()
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug("V20CredAckHandler called with context %s", context)
        assert isinstance(context.message, V20CredAck)
        _logger.info(
            "Received v2.0 credential ack message: %s",
            context.message.serialize(as_string=True),
        )

        # If connection is present it must be ready for use
        if context.connection_record and not context.connection_ready:
            raise HandlerException("Connection used for credential ack not ready")

        # Find associated oob record
        oob_processor = context.inject(OobMessageProcessor)
        oob_record = await oob_processor.find_oob_record_for_inbound_message(context)

        # Either connection or oob context must be present
        if not context.connection_record and not oob_record:
            raise HandlerException(
                "No connection or associated connectionless exchange found for credential"
                " ack"
            )

        cred_manager = V20CredManager(context.profile)
        await cred_manager.receive_credential_ack(
            context.message,
            context.connection_record.connection_id
            if context.connection_record
            else None,
        )

        trace_event(
            context.settings,
            context.message,
            outcome="V20CredAckHandler.handle.END",
            perf_counter=r_time,
        )
