"""DIDComm V2 Agent message base class and schema."""

from uuid import uuid4

from .base_message import BaseMessage, DIDCommVersion
from .models.base import BaseModel


class V2AgentMessage(BaseMessage):
    """DIDComm V2 message base class."""

    def __init__(self, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message
        self.msg_format = DIDCommVersion.v2
        if not "id" in self.message:
            self.message["id"] = str(uuid4())

    @property
    def _message_type(self):
        return self.message.get("type")

    @property
    def _type(self):
        return self.message.get("type")

    @property
    def _id(self):
        return self.message.get("id")

    @property
    def _thread_id(self):
        return self.message.get("thid", self.message.get("id"))

    def serialize(self, msg_format: DIDCommVersion = DIDCommVersion.v1) -> dict:
        return self.message

    def deserialize(cls, value: dict, msg_format: DIDCommVersion = DIDCommVersion.v2):
        self.message = value
        self.msg_format = msg_format

    @property
    def Handler(self):
        return None
