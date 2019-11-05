"""Basic message handler."""

import json

from ....holder.base import BaseHolder
from ....messaging.base_handler import BaseHandler, BaseResponder, RequestContext

from ..manager import PresentationManager
from ..messages.presentation_request import PresentationRequest


class PresentationRequestHandler(BaseHandler):
    """Message handler class for presentation requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for presentation requests.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"PresentationRequestHandler called with context {context}")

        assert isinstance(context.message, PresentationRequest)

        self._logger.info("Received presentation request: %s", context.message.request)

        presentation_manager = PresentationManager(context)

        presentation_exchange_record = await presentation_manager.receive_request(
            context.message, context.connection_record.connection_id
        )

        # If auto_respond_presentation_request is set, try to build a presentation
        # This will fail and bail out if there isn't exactly one credential returned
        # for each requested attribute and predicate. All credential data will be
        # revealed.
        if context.settings.get("debug.auto_respond_presentation_request"):
            holder: BaseHolder = await context.inject(BaseHolder)
            credentials_for_presentation = {
                "self_attested_attributes": {},
                "requested_attributes": {},
                "requested_predicates": {},
            }

            presentation_request = json.loads(context.message.request)

            for referent in presentation_request["requested_attributes"]:
                (
                    credentials
                ) = await holder.get_credentials_for_presentation_request_by_referent(
                    presentation_request, (referent,), 0, 2, {}
                )
                if len(credentials) != 1:
                    self._logger.warning(
                        f"Could not automatically construct presentation for"
                        + f" presentation request {presentation_request['name']}"
                        + f":{presentation_request['version']} because referent "
                        + f"{referent} did not produce exactly one credential result."
                        + f" {len(credentials)} credentials were returned from the "
                        + f"wallet."
                    )
                    return

                credentials_for_presentation["requested_attributes"][referent] = {
                    "cred_id": credentials[0]["cred_info"]["referent"],
                    "revealed": True,
                }

            for referent in presentation_request["requested_predicates"]:
                (
                    credentials
                ) = await holder.get_credentials_for_presentation_request_by_referent(
                    presentation_request, (referent,), 0, 2, {}
                )
                if len(credentials) != 1:
                    self._logger.warning(
                        f"Could not automatically construct presentation for"
                        + f" presentation request {presentation_request['name']}"
                        + f":{presentation_request['version']} because referent "
                        + f"{referent} did not produce exactly one credential result."
                        + f" {len(credentials)} credentials were returned from the "
                        + f"wallet."
                    )
                    return

                credentials_for_presentation["requested_predicates"][referent] = {
                    "cred_id": credentials[0]["cred_info"]["referent"],
                    "revealed": True,
                }

            (
                presentation_exchange_record,
                presentation_message,
            ) = await presentation_manager.create_presentation(
                presentation_exchange_record, credentials_for_presentation
            )

            await responder.send_reply(presentation_message)
