"""Problem report handler for DID Exchange."""

from .....connections.models.conn_record import ConnRecord
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from .....storage.error import StorageNotFoundError
from ..manager import DIDXManager, DIDXManagerError
from ..messages.problem_report import DIDXProblemReport


class DIDXProblemReportHandler(BaseHandler):
    """Handler class for DID Exchange problem report messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle problem report message."""
        self._logger.debug(f"DIDXProblemReportHandler called with context {context}")
        assert isinstance(context.message, DIDXProblemReport)

        self._logger.info("Received problem report: %s", context.message.description)
        profile = context.profile
        mgr = DIDXManager(profile)
        try:
            conn_rec = context.connection_record
            if not conn_rec:
                # try to find connection by thread_id/request_id
                try:
                    async with profile.session() as session:
                        conn_rec = await ConnRecord.retrieve_by_request_id(
                            session, context.message._thread_id
                        )
                except StorageNotFoundError:
                    pass

            if conn_rec:
                await mgr.receive_problem_report(conn_rec, context.message)
            else:
                raise HandlerException("No connection established for problem report")
        except DIDXManagerError:
            # Unrecognized problem report code
            self._logger.exception("Error receiving DID Exchange problem report")
