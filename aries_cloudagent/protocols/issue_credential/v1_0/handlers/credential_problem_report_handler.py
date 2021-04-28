"""Credential ack message handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)
from .....storage.error import StorageError, StorageNotFoundError

from ..manager import CredentialManager
from ..messages.credential_problem_report import IssueCredentialV10ProblemReport


class CredentialProblemReportHandler(BaseHandler):
    """Message handler class for credential acks."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for problem reports.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(
            "Issue-credential v1.0 ProblemReportHandler called with context %s",
            context,
        )
        assert isinstance(context.message, IssueCredentialV10ProblemReport)

        credential_manager = CredentialManager(context.profile)
        try:
            await credential_manager.receive_problem_report(
                context.message,
                context.connection_record.credential_exchange_id,
            )
        except (StorageError, StorageNotFoundError):
            self._logger.exception(
                "Error processing issue-credential v1.0 Problem Report message"
            )
