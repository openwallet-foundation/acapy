"""Represents the attached message to be included in the transaction record."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import ATTACHED_MESSAGE


SCHEMA_TYPE = "101"
PROTOCOL_VERSION = "2"


class MessagesAttach(AgentMessage):
    """Class representing the attached message."""

    class Meta:
        """Metadata for attached message class."""

        schema_class = "MessagesAttachSchema"
        message_type = ATTACHED_MESSAGE

    def __init__(
        self,
        *,
        author_did: str = None,
        author_verkey: str = None,
        endorser_did: str = None,
        attr_names: list = [],
        name: str = None,
        version: str = None,
        mechanism: str = None,
        taaDigest: str = None,
        time: int = None,
        **kwargs
    ):
        """
        Initialize the attached message object.

        Args:
            author_did: The public did of the author who creates the transaction
            author_verkey: The verkey of the author who creates the transaction
            endorser_did: The public did of the endorser who endorses the transaction
            attr_names: The name of attributes present in the schema transaction
            name: The name of schema
            version: The version of schema
            mechanism: The mechanism of the latest TAA present on the ledger
            taaDigest: The digest of the latest TAA present on the ledger
            time: The time when the latest TAA was set/enabled
        """

        super().__init__(**kwargs)

        self.mime_type = "application/json"

        self.data = {
            "json": {
                "endorser": endorser_did,
                "identifier": author_did,
                "operation": {
                    "data": {
                        "attr_names": attr_names,
                        "name": name,
                        "version": version,
                    },
                    "type": SCHEMA_TYPE,
                },
                "protocol_version": PROTOCOL_VERSION,
                "reqId": 1597766666168851000,
                "signatures": {author_did: author_verkey},
                "taaAcceptance": {
                    "mechanism": mechanism,
                    "taaDigest": taaDigest,
                    "time": time,
                },
            }
        }


class MessagesAttachSchema(AgentMessageSchema):
    """Attached Message schema class."""

    class Meta:
        """Attached message schema metadata."""

        model_class = MessagesAttach
        unknown = EXCLUDE

    mime_type = fields.Str(required=True)
    data = fields.Dict(required=True)
