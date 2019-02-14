"""
An object for containing the connection request/response DID information
"""

import json

from marshmallow import fields

from . import BaseModel, BaseModelSchema
from von_anchor.a2a import DIDDoc


class DIDDocWrapper(fields.Field):
    """
    Field that loads and serializes DIDDoc
    """
    def _serialize(self, value, attr, obj, **kwargs):
        return value.serialize()

    def _deserialize(self, value, attr, data, **kwargs):
        # quick fix for missing optional values
        if "authentication" not in value:
            value["authentication"] = []
        if "service" not in value:
            value["service"] = []
        return DIDDoc.deserialize(value)


class ConnectionDetail(BaseModel):
    class Meta:
        schema_class = 'ConnectionDetailSchema'

    def __init__(
            self,
            *,
            did: str = None,
            did_doc: DIDDoc = None,
            **kwargs
        ):
        super(ConnectionDetail, self).__init__(**kwargs)
        self._did = did
        self._did_doc = did_doc

    @property
    def did(self) -> str:
        """
        Accessor for the connection DID
        """
        return self._did
    
    @property
    def did_doc(self) -> DIDDoc:
        """
        Accessor for the connection DID Document
        """
        return self._did_doc


class ConnectionDetailSchema(BaseModelSchema):
    class Meta:
        model_class = 'ConnectionDetail'

    did = fields.Str(data_key="DID")
    did_doc = DIDDocWrapper(data_key="DIDDoc", required=False)
