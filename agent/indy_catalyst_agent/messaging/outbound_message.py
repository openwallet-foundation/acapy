"""Outbound message representation."""

from typing import Union

from .connections.models.connection_target import ConnectionTarget


class OutboundMessage:
    """Represents an outgoing message."""

    def __init__(
        self,
        payload: Union[str, bytes],
        *,
        connection_id: str = None,
        encoded: bool = False,
        endpoint: str = None,
        reply_socket_id: str = None,
        reply_thread_id: str = None,
        reply_to_verkey: str = None,
        target: ConnectionTarget = None,
    ):
        """Initialize an outgoing message."""
        self.connection_id = connection_id
        self.encoded = encoded
        self._endpoint = endpoint
        self.payload = payload
        self.reply_socket_id = reply_socket_id
        self.reply_thread_id = reply_thread_id
        self.reply_to_verkey = reply_to_verkey
        self.target = target

    @property
    def endpoint(self) -> str:
        """Return the endpoint of the outbound message.

        Defaults to the endpoint of the connection target.
        """
        return self._endpoint or (self.target and self.target.endpoint)

    @endpoint.setter
    def endpoint(self, endp: str) -> None:
        """Set the endpoint of the outbound message."""
        self._endpoint = endp

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
