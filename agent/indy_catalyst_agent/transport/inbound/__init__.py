from collections import namedtuple

from abc import ABC, abstractmethod
from typing import Callable

from ...error import BaseError

InboundTransportConfiguration = namedtuple(
    "InboundTransportConfiguration", "module host port"
)


class InvalidTransportError(BaseError):
    pass
