"""Connection request handler."""

import logging

from .....config.logging import get_logger_inst
from .....connections.models.conn_record import ConnRecord
from .....messaging.base_handler import BaseHandler, BaseResponder, RequestContext
from ....coordinate_mediation.v1_0.manager import MediationManager

from ..manager import ConnectionManager, ConnectionManagerError
from ..messages.connection_request import ConnectionRequest
from ..messages.problem_report import ConnectionProblemReport


class ConnectionRequestHandler(BaseHandler):
    """Handler class for connection requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle connection request.

        Args:
            context: Request context
            responder: Responder callback
        """
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug(f"ConnectionRequestHandler called with context {context}")
        assert isinstance(context.message, ConnectionRequest)

        profile = context.profile
        mgr = ConnectionManager(profile)

        mediation_id = None
        if context.connection_record:
            async with profile.session() as session:
                mediation_metadata = await context.connection_record.metadata_get(
                    session, MediationManager.METADATA_KEY, {}
                )
            mediation_id = mediation_metadata.get(MediationManager.METADATA_ID)

        try:
            connection = await mgr.receive_request(
                context.message,
                context.message_receipt,
            )

            if connection.accept == ConnRecord.ACCEPT_AUTO:
                response = await mgr.create_response(
                    connection, mediation_id=mediation_id
                )
                await responder.send_reply(
                    response, connection_id=connection.connection_id
                )
            else:
                _logger.debug("Connection request will await acceptance")
        except ConnectionManagerError as e:
            _logger.exception("Error receiving connection request")
            if e.error_code:
                targets = None
                if context.message.connection and context.message.connection.did_doc:
                    try:
                        targets = mgr.diddoc_connection_targets(
                            context.message.connection.did_doc,
                            context.message_receipt.recipient_verkey,
                        )
                    except ConnectionManagerError:
                        _logger.exception("Error parsing DIDDoc for problem report")
                await responder.send_reply(
                    ConnectionProblemReport(problem_code=e.error_code, explain=str(e)),
                    target_list=targets,
                )
