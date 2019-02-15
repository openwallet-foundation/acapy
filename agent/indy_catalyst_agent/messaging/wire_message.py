"""
Represents a wire message.
"""

from marshmallow import Schema, fields


class WireMessage:
    """Class representing a wire message."""
    def __init__(self, _from: str, to: str, msg: str):
        self._from = _from
        self.to = to
        self.msg = msg


class WireMessageSchema(Schema):
    """Wire message schema."""
    # Avoid clobbering builtin property
    _from = fields.Str(data_key="from")
    to = fields.Str()
    msg = fields.Str()
