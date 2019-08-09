"""Aries#0037 v1.0 Presentation request handler."""


from ....base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext
)

from .....holder.base import BaseHolder
from .....storage.error import StorageNotFoundError

from ..manager import PresentationManager
from ..messages.inner.presentation_preview import PresentationPreview
from ..messages.presentation_request import PresentationRequest
from ..messages.presentation_proposal import PresentationProposal
from ..models.presentation_exchange import V10PresentationExchange


class PresentationRequestHandler(BaseHandler):
    """Message handler class for Aries#0037 v1.0 presentation requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for Aries#0037 v1.0 presentation requests.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"PresentationRequestHandler called with context {context}")

        assert isinstance(context.message, PresentationRequest)

        self._logger.info(
            "Received presentation request: %s",
            context.message.serialize(as_string=True)
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for presentation request")

        presentation_manager = PresentationManager(context)

        indy_proof_request = context.message.indy_proof_request(0)
        presentation_proposal_dict = PresentationProposal(
            comment=context.message.comment,
            presentation_proposal=PresentationPreview.from_indy_proof_request(
                indy_proof_request
            )
        ).serialize()

        # Get credential exchange record (holder sent proposal first)
        # or create it (verifier sent request first)
        try:
            presentation_exchange_record = (
                await V10PresentationExchange.retrieve_by_tag_filter(
                    context,
                    {
                        "thread_id": context.message._thread_id
                    }
                )
            )
            presentation_exchange_record.presentation_proposal_dict = (
                presentation_proposal_dict
            )
        except StorageNotFoundError:  # verifier sent this request free of any proposal
            presentation_exchange_record = V10PresentationExchange(
                connection_id=context.connection_record.connection_id,
                thread_id=context.message._thread_id,
                initiator=V10PresentationExchange.INITIATOR_EXTERNAL,
                presentation_proposal_dict=presentation_proposal_dict,
                presentation_request=indy_proof_request,
                auto_present=context.settings.get(
                    "debug.auto_respond_presentation_request"
                )
            )

        presentation_exchange_record.presentation_request = indy_proof_request

        presentation_exchange_record = await presentation_manager.receive_request(
            presentation_exchange_record
        )

        # If auto_present is enabled, respond immediately with presentation
        if presentation_exchange_record.auto_present:
            hold: BaseHolder = await context.inject(BaseHolder)
            req_creds = {
                "self_attested_attributes": {},
                "requested_attributes": {},
                "requested_predicates": {}
            }

            for category in ("requested_attributes", "requested_predicates"):
                for referent in indy_proof_request[category]:
                    credentials = (
                        await hold.get_credentials_for_presentation_request_by_referent(
                            indy_proof_request,
                            (referent,),
                            0,
                            2,
                            {}
                        )
                    )
                    if len(credentials) != 1:
                        self._logger.warning(
                            f"Could not automatically construct presentation for "
                            + f"presentation request {indy_proof_request['name']}"
                            + f":{indy_proof_request['version']} because referent "
                            + f"{referent} did not produce exactly one credential "
                            + f"result. The wallet returned {len(credentials)} "
                            + f"matching credentials."
                        )
                        return

                    req_creds[category][referent] = {
                        "cred_id": credentials[0]["cred_info"]["referent"],
                        "revealed": True
                    }

            (
                presentation_exchange_record,
                presentation_message
            ) = await presentation_manager.create_presentation(
                presentation_exchange_record=presentation_exchange_record,
                requested_credentials=req_creds,
                comment="auto-presented for proof request nonce={}".format(
                    indy_proof_request["nonce"]
                )
            )

            await responder.send_reply(presentation_message)
