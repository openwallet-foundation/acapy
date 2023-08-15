"""Connection request handler under RFC 23 (DID exchange)."""

from aries_cloudagent.protocols.didexchange.v1_0.messages.problem_report import (
    DIDXProblemReport,
)
from .....connections.models.conn_record import ConnRecord
from .....messaging.base_handler import BaseHandler, BaseResponder, RequestContext
from ....coordinate_mediation.v1_0.manager import MediationManager
from ..manager import DIDXManager, DIDXManagerError
from ..messages.request import DIDXRequest


class DIDXRequestHandler(BaseHandler):
    """Handler class for connection request message under RFC 23 (DID exchange)."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection request under RFC 23 (DID exchange).

        Args:
            context: Request context
            responder: Responder callback
        """

        self._logger.debug(f"DIDXRequestHandler called with context {context}")
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
                response = await mgr.create_response(
                    conn_rec,
                    mediation_id=mediation_id,
                )
                await responder.send_reply(
                    response, connection_id=conn_rec.connection_id
                )
                conn_rec.state = ConnRecord.State.RESPONSE.rfc23
                async with context.session() as session:
                    await conn_rec.save(session, reason="Sent connection response")
            else:
                self._logger.debug("DID exchange request will await acceptance")

        except DIDXManagerError as e:
            self._logger.exception("Error receiving RFC 23 connection request")
            if e.error_code:
                targets = None
                if context.message.did_doc_attach:
                    try:
                        targets = mgr.diddoc_connection_targets(
                            context.message.did_doc_attach,
                            context.message_receipt.recipient_verkey,
                        )
                    except DIDXManagerError:
                        self._logger.exception(
                            "Error parsing DIDDoc for problem report"
                        )
                await responder.send_reply(
                    DIDXProblemReport(
                        description={"en": e.message, "code": e.error_code}
                    ),
                    target_list=targets,
                )
