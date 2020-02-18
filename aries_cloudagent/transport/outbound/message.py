"""Outbound message representation."""

from typing import Sequence, Union

from ...connections.models.connection_target import ConnectionTarget


class OutboundMessage:
    """Represents an outgoing message."""

    def __init__(
        self,
        *,
        connection_id: str = None,
        enc_payload: Union[str, bytes] = None,
        endpoint: str = None,
        payload: Union[str, bytes],
        reply_session_id: str = None,
        reply_thread_id: str = None,
        reply_to_verkey: str = None,
        reply_from_verkey: str = None,
        target: ConnectionTarget = None,
        target_list: Sequence[ConnectionTarget] = None,
        to_session_only: bool = False,
    ):
        """Initialize an outgoing message."""
        self.connection_id = connection_id
        self.enc_payload = enc_payload
        self._endpoint = endpoint
        self.payload = payload
        self.reply_session_id = reply_session_id
        self.reply_thread_id = reply_thread_id
        self.reply_to_verkey = reply_to_verkey
        self.reply_from_verkey = reply_from_verkey
        self.target = target
        self.target_list = list(target_list) if target_list else []
        self.to_session_only = to_session_only

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
