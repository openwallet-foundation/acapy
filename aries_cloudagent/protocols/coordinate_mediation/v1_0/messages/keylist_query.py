"""A mediation keylist query content message."""

from marshmallow import fields

from ....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import KEYLIST_QUERY, PROTOCOL_PACKAGE

from .inner.keylist_query_paginate import (
    KeylistQueryPaginate,
    KeylistQueryPaginateSchema
)


HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".keylist_query_request_handler.KeylistQueryRequestHandler"
)


class KeylistQuery(AgentMessage):
    """Class representing a keylist query message."""

    class Meta:
        """Metadata for a keylist query."""

        handler_class = HANDLER_CLASS
        message_type = KEYLIST_QUERY
        schema_class = "KeylistQuerySchema"

    def __init__(
        self,
        *,
        filter: dict = None,
        paginate: KeylistQueryPaginate = None,
        **kwargs,
    ):
        """
        Initialize keylist query object.

        Args:
            filter: Filter for query
            paginate: Pagination rules
        """
        super(KeylistQuery, self).__init__(**kwargs)
        self.filter = filter
        self.paginate = paginate


class KeylistQuerySchema(AgentMessageSchema):
    """Keylist query schema class."""

    class Meta:
        """Keylist query schema metadata."""

        model_class = KeylistQuery

    filter = fields.Dict(
        description="Query dictionary object",
        example={
            "routing_key": [
                "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
                "2wUJCoyzkJz1tTxehfT7Usq5FgJz3EQHBQC7b2mXxbRZ"
            ]
        }
    )
    paginate = fields.Nested(
        KeylistQueryPaginateSchema(),
        description="List of update rules"
    )
