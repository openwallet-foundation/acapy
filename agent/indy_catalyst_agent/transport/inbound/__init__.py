from collections import namedtuple

from abc import ABC, abstractmethod
from typing import Callable

InboundTransportConfiguration = namedtuple(
    "InboundTransportConfiguration", "module host port"
)


class InvalidTransportError(Exception):
    pass
