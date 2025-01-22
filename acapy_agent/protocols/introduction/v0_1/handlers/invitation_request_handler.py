"""Handler for incoming invitation request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from ....out_of_band.v1_0.manager import OutOfBandManager
from ....out_of_band.v1_0.messages.invitation import HSProto
from ..messages.invitation import Invitation as IntroInvitation
from ..messages.invitation_request import InvitationRequest as IntroInvitationRequest


class InvitationRequestHandler(BaseHandler):
    """Handler for incoming invitation request messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("InvitationRequestHandler called with context %s", context)
        assert isinstance(context.message, IntroInvitationRequest)

        if not context.connection_ready:
            raise HandlerException(
                "No connection established for introduction invitation request message"
            )

        # Need a way to prompt the user for acceptance?

        if context.settings.get("auto_accept_intro_invitation_requests"):
            # Create a new connection invitation and send it back in an IntroInvitation
            profile = context.profile
            mgr = OutOfBandManager(profile)
            invite = await mgr.create_invitation(
                use_did_method="did:peer:4",
                hs_protos=[HSProto.DIDEX_1_1],
            )
            response = IntroInvitation(
                invitation=invite.invitation, message=context.message.message
            )
            response.assign_thread_from(context.message)
            response.assign_trace_from(context.message)
            await responder.send_reply(response)
