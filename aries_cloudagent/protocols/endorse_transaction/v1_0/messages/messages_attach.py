from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema


SCHEMA_TYPE = "101"
PROTOCOL_VERSION = "2"

class MessagesAttach(AgentMessage):

    class Meta:

        schema_class = "MessagesAttachSchema"


    def __init__(
                self, 
                *,
                author_did:str = None, 
                endorser_did:str = None, 
                attr_names:list = [], 
                name:str = None, 
                version:str = None, 
                **kwargs
                ):

        self.mime_type = "application/json"

        self.data = {
            "json":{
                "endorser": author_did,
                "identifier": endorser_did,
                "operation": {
                    "data": {
                        "attr_names": attr_names,
                        "name": name,
                        "version": version
                    },
                    "type": SCHEMA_TYPE
                },
                "protocol_version": PROTOCOL_VERSION,
                "reqId": 1597766666168851000,
                "signatures": {
                    "LjgpST2rjsoxYegQDRm7EL": "4uq1mUATKMn6Y9sTgwqaGWGTTsYm7py2c2M8x1EVDTWKZArwyuPgjUEw5UBysWNbkf2SN6SqVwbfSqCfnbm1Vnfw"
                    },
                "taaAcceptance": { 
                    "mechanism": "manual",
                    "taaDigest": "f50feca75664270842bd4202c2ab977006761d36bd6f23e4c6a7e0fc2feb9f62",
                    "time": 1597708800
                    }                
            }
        }


class MessagesAttachSchema(AgentMessageSchema):

    class Meta:

        model_class = MessagesAttach
        unknown = EXCLUDE

    mime_type = fields.Str(
        required=True
    )

    data = fields.Dict(
        required=True
    )


