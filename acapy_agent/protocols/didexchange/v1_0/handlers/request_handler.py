"""Connection request handler under RFC 23 (DID exchange)."""

from .....connections.models.conn_record import ConnRecord
from .....messaging.base_handler import BaseHandler, BaseResponder, RequestContext
from ....coordinate_mediation.v1_0.manager import MediationManager
from ..manager import DIDXManager, DIDXManagerError
from ..messages.request import DIDXRequest


class DIDXRequestHandler(BaseHandler):
    """Handler class for connection request message under RFC 23 (DID exchange)."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle connection request under RFC 23 (DID exchange).

        Args:
            context: Request context
            responder: Responder callback

        """
        self._logger.debug("DIDXRequestHandler called with context %s", context)
        assert isinstance(context.message, DIDXRequest)

        profile = context.profile
        mgr = DIDXManager(profile)

        mediation_id = None
        if context.connection_record:
            async with profile.session() as session:
                mediation_metadata = await context.connection_record.metadata_get(
                    session, MediationManager.METADATA_KEY, {}
                )
            mediation_id = mediation_metadata.get(MediationManager.METADATA_ID)

        try:
            conn_rec = await mgr.receive_request(
                request=context.message,
                recipient_did=context.message_receipt.recipient_did,
                recipient_verkey=(
                    None
                    if context.message_receipt.recipient_did_public
                    else context.message_receipt.recipient_verkey
                ),
            )
            # Auto respond
            if conn_rec.accept == ConnRecord.ACCEPT_AUTO:
                # create_response() already transitions conn_rec to the response
                # state and persists it. Do not set/save that state again after
                # sending: in a self-connection, delivering the response can
                # synchronously drive the rest of the handshake (accept_response
                # -> complete -> accept_complete) to completion before
                # send_reply() returns, and blindly overwriting the state here
                # would regress an already-completed connection back to
                # "response".
                response = await mgr.create_response(
                    conn_rec,
                    mediation_id=mediation_id,
                )
                await responder.send_reply(response, connection_id=conn_rec.connection_id)
            else:
                self._logger.debug("DID exchange request will await acceptance")

        except DIDXManagerError as e:
            report, targets = await mgr.manager_error_to_problem_report(
                e, context.message, context.message_receipt
            )
            if report and targets:
                await responder.send_reply(
                    message=report,
                    target_list=targets,
                )
