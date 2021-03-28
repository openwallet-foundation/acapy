"""Credential request message handler."""

from aries_cloudagent.protocols.issue_credential.v2_0.messages.cred_proposal import (
    V20CredProposal,
)
from aries_cloudagent.protocols.issue_credential.v2_0.messages.cred_format import (
    V20CredFormat,
)
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import V20CredManager
from ..messages.cred_request import V20CredRequest

from .....utils.tracing import trace_event, get_timer


class V20CredRequestHandler(BaseHandler):
    """Message handler class for credential requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential requests.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = get_timer()

        self._logger.debug("V20CredRequestHandler called with context %s", context)
        assert isinstance(context.message, V20CredRequest)
        self._logger.info(
            "Received v2.0 credential request message: %s",
            context.message.serialize(as_string=True),
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for credential request")

        cred_manager = V20CredManager(context.profile)
        cred_ex_record = await cred_manager.receive_request(
            context.message, context.connection_record.connection_id
        )

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="V20CredRequestHandler.handle.END",
            perf_counter=r_time,
        )

        # If auto_issue is enabled, respond immediately
        if cred_ex_record.auto_issue:
            cred_formats = [
                V20CredFormat.Format.get(format.format)
                for format in context.message.formats
            ]

            # TODO: this should be removed here and handled in the format
            # specific handler. This way we don't bloat this file
            can_respond_indy = (
                V20CredFormat.Format.INDY in cred_formats
                and V20CredProposal.deserialize(
                    cred_ex_record.cred_proposal
                ).credential_preview
            )
            can_respond_ld_proof = V20CredFormat.Format.LD_PROOF in cred_formats

            if can_respond_indy or can_respond_ld_proof:
                (
                    cred_ex_record,
                    cred_issue_message,
                ) = await cred_manager.issue_credential(
                    cred_ex_record=cred_ex_record, comment=context.message.comment
                )

                await responder.send_reply(cred_issue_message)

                trace_event(
                    context.settings,
                    cred_issue_message,
                    outcome="V20CredRequestHandler.issue.END",
                    perf_counter=r_time,
                )
            else:
                self._logger.warning(
                    "Operation set for auto-issue but v2.0 credential exchange record "
                    f"{cred_ex_record.cred_ex_id} "
                    "has no attribute values"
                )
