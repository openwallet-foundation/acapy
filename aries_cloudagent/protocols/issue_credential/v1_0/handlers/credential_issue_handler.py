"""Credential issue message handler."""

from .....indy.holder import IndyHolderError
from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageError
from .....utils.tracing import trace_event, get_timer

from ..manager import CredentialManager, CredentialManagerError
from ..messages.credential_issue import CredentialIssue


class CredentialIssueHandler(BaseHandler):
    """Message handler class for credential offers."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential offers.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = get_timer()

        self._logger.debug("CredentialHandler called with context %s", context)
        assert isinstance(context.message, CredentialIssue)
        self._logger.info(
            "Received credential message: %s", context.message.serialize(as_string=True)
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for credential issue")

        credential_manager = CredentialManager(context.profile)
        cred_ex_record = await credential_manager.receive_credential(
            context.message, context.connection_record.connection_id
        )  # mgr only finds, saves record: on exception, saving state null is hopeless

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="CredentialIssueHandler.handle.END",
            perf_counter=r_time,
        )

        # Automatically move to next state if flag is set
        if context.settings.get("debug.auto_store_credential"):
            try:
                cred_ex_record = await credential_manager.store_credential(
                    cred_ex_record
                )
            except (CredentialManagerError, IndyHolderError, StorageError) as err:
                # protocol finished OK: do not set cred ex record state null
                self._logger.exception(err)

            credential_ack_message = await credential_manager.send_credential_ack(
                cred_ex_record
            )

            trace_event(
                context.settings,
                credential_ack_message,
                outcome="CredentialIssueHandler.handle.STORE",
                perf_counter=r_time,
            )
