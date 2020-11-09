"""Connection handling admin routes."""

import json

from typing import Mapping, Union

from marshmallow import fields, pre_dump, validate, validates_schema, ValidationError

from ....connections.models.connection_record import (
    ConnectionRecord,
    ConnectionRecordSchema,
)
from ....connections.models.conn23rec import (
    Conn23Record,
    Conn23RecordSchema,
)
from ....messaging.models.openapi import OpenAPISchema


class ConnResult(fields.Field):
    """RFC 23 or RFC 160 connection record."""

    def _serialize(
        self,
        value: Union[ConnectionRecord, Conn23Record],
        attr,
        obj,
        **kwargs
    ):
        return None if value is None else value.serialize()

    def _deserialize(
        self,
        value: Mapping,
        attr,
        data,
        **kwargs
    ):
        if value is None:
            return None
        try:
            return Conn23Record.deserialize(value)
        except ValidationError:
            return ConnectionRecord.deserialize(value)

class ConnResultSchema(OpenAPISchema):
    """Connection result."""

    result = ConnResult(
        required=True,
        description="Connection record"
    )


'''
class ConnListSchema(OpenAPISchema):
    """."""

    results = fields.List(
        fields.Pluck(ConnResultSchema(), "result"),
        description="List of connection records",
    )
'''
