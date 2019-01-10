"""
An object for containing agent endpoint information.
"""


from marshmallow import Schema, fields


class AgentEndpoint:
    def __init__(self, did, verkey, uri):
        self.did = did
        self.verkey = verkey
        self.uri = uri


class AgentEndpointSchema(Schema):
    did = fields.Str()
    verkey = fields.Str()
    uri = fields.Str()
