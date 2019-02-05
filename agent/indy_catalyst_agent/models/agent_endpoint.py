"""
An object for containing agent endpoint information.
"""


from marshmallow import Schema, fields

from . import BaseModel, BaseModelSchema


class AgentEndpoint(BaseModel):
    class Meta:
        schema_class = 'AgentEndpointSchema'

    def __init__(
            self,
            *,
            did: str = None,
            verkey: str = None,
            uri: str = None,
            **kwargs
        ):
        super(AgentEndpoint, self).__init__(**kwargs)
        self.did = did
        self.verkey = verkey
        self.uri = uri


class AgentEndpointSchema(BaseModelSchema):
    class Meta:
        model_class = 'AgentEndpoint'

    did = fields.Str()
    verkey = fields.Str()
    uri = fields.Str()
