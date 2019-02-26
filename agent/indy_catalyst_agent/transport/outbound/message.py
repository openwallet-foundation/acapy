"""Data shape for outbound message."""

from collections import namedtuple

OutboundMessage = namedtuple("OutboundMessage", "data uri")
