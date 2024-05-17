"""DIDComm V2 Agent message base class and schema."""

from .base_message import BaseMessage
from .models.base import BaseModel


class V2AgentMessage(BaseModel, BaseMessage):
    """DIDComm V2 message base class."""

    class Meta:
        """DIDComm V2 message metadats."""

        schema_class = None
        message_type = None
