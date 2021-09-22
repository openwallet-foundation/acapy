"""DID exchange response handler under RFC 23."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ....problem_report.v1_0.message import ProblemReport
from ....trustping.v1_0.messages.ping import Ping

from ..manager import DIDXManager, DIDXManagerError
from ..messages.response import DIDXResponse


class DIDXResponseHandler(BaseHandler):
    """Handler class for DID exchange response message under RFC 23."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle DID exchange response under RFC 23.

        Args:
            context: Request context
            responder: Responder callback
        """
        self._logger.debug(f"DIDXResponseHandler called with context {context}")
        assert isinstance(context.message, DIDXResponse)

        profile = context.profile
        mgr = DIDXManager(profile)
        try:
            conn_rec = await mgr.accept_response(
                context.message, context.message_receipt
            )
        except DIDXManagerError as e:
            self._logger.exception("Error receiving DID exchange response")
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
            return

        # send trust ping in response
        if context.settings.get("auto_ping_connection"):
            await responder.send(Ping(), connection_id=conn_rec.connection_id)
