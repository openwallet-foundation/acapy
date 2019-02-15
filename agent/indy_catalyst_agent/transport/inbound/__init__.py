from collections import namedtuple

from ...error import BaseError

InboundTransportConfiguration = namedtuple(
    "InboundTransportConfiguration", "module host port"
)


class InvalidTransportError(BaseError):
    pass
