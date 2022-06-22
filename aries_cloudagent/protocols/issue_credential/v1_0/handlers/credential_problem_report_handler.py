"""Credential problem report message handler."""

from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageError, StorageNotFoundError

from ..manager import CredentialManager
from ..messages.credential_problem_report import CredentialProblemReport


class CredentialProblemReportHandler(BaseHandler):
    """Message handler class for problem reports."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for problem reports.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(
            "Issue-credential v1.0 problem report handler called with context %s",
            context,
        )
        assert isinstance(context.message, CredentialProblemReport)

        # If connection is present it must be ready for use
        if context.connection_record and not context.connection_ready:
            raise HandlerException(
                "Connection used for credential problem report not ready"
            )
        elif not context.connection_record:
            raise HandlerException(
                "Connectionless not supported for credential problem report"
            )

        credential_manager = CredentialManager(context.profile)
        try:
            await credential_manager.receive_problem_report(
                context.message,
                context.connection_record.connection_id,
            )
        except (StorageError, StorageNotFoundError):
            self._logger.exception(
                "Error processing issue-credential v1.0 problem report message"
            )
