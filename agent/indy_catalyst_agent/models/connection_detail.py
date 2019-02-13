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
        # FIXME - not ideal! need a separate method on DIDDoc
        #return value.serialize()
        dd_json = value.to_json()
        return json.loads(dd_json)

    def _deserialize(self, value, attr, data, **kwargs):
        # FIXME - same as above
        #return DIDDoc.deserialize(value)
        dd_json = json.dumps(value)
        return DIDDoc.from_json(dd_json)


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
