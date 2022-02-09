"""Connection request handler under RFC 23 (DID exchange)."""

from .....messaging.base_handler import BaseHandler, BaseResponder, RequestContext

from ....problem_report.v1_0.message import ProblemReport

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

        session = await context.session()
        mgr = DIDXManager(session)
        if context.connection_record:
            mediation_metadata = await context.connection_record.metadata_get(
                session, "mediation", {}
            )
        else:
            mediation_metadata = {}
        try:
            await mgr.receive_request(
                request=context.message,
                recipient_did=context.message_receipt.recipient_did,
                recipient_verkey=(
                    None
                    if context.message_receipt.recipient_did_public
                    else context.message_receipt.recipient_verkey
                ),
                mediation_id=mediation_metadata.get("id"),
            )
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
                    ProblemReport(description={"en": e.message, "code": e.error_code}),
                    target_list=targets,
                )
