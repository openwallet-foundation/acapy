"""keylist-query message used to request list of keys handled by mediator."""

from marshmallow import fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import KEYLIST_QUERY, PROTOCOL_PACKAGE

from .inner.keylist_query_paginate import (
    KeylistQueryPaginate,
    KeylistQueryPaginateSchema,
)


HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.keylist_query_handler.KeylistQueryHandler"


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
        super().__init__(**kwargs)
        self.filter = filter
        self.paginate = paginate


class KeylistQuerySchema(AgentMessageSchema):
    """Keylist query schema class."""

    class Meta:
        """Keylist query schema metadata."""

        model_class = KeylistQuery

    filter = fields.Dict(
        required=False,
        description="Query dictionary object",
        example={"filter": {}},
    )
    paginate = fields.Nested(
        KeylistQueryPaginateSchema(), required=False, description="Pagination info"
    )
