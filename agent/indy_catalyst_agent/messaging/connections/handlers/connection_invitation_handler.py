import logging

from typing import Callable

from ...base_handler import BaseHandler

# from ..messages.connection_invitation import ConnectionInvitation


class ConnectionInvitationHandler(BaseHandler):
    def __init__(self, message: "ConnectionInvitation") -> None:
        self.logger = logging.getLogger(__name__)
        self.message = message

    def handle(self, thread_state, callback: Callable):
        self.logger.debug(
            "ConnectionInvitationHandler called with thread_state "
            + f"{thread_state} and callback {callback}"
        )
