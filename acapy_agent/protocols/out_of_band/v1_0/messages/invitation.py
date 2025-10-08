"""An invitation content message."""

from enum import Enum
from typing import NamedTuple, Optional, Sequence, Set, Text, Union
from urllib.parse import parse_qs, urljoin, urlparse

from marshmallow import EXCLUDE, ValidationError, fields, post_dump, validates_schema

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from .....messaging.valid import DIDValidation
from .....wallet.util import b64_to_bytes, bytes_to_b64
from ....didcomm_prefix import DIDCommPrefix
from ....didexchange.v1_0.message_types import ARIES_PROTOCOL as DIDEX_1_1
from ....didexchange.v1_0.message_types import DIDEX_1_0
from ..message_types import DEFAULT_VERSION, INVITATION
from .service import Service


class HSProtoSpec(NamedTuple):
    """Handshake protocol specification."""

    name: str
    aka: Set[str]


class HSProto(Enum):
    """Handshake protocol enum for invitation message."""

    RFC160 = HSProtoSpec(
        "connections/1.0",
        {"connection", "connections", "conn", "conns", "rfc160", "160", "old"},
    )
    RFC23 = HSProtoSpec(
        DIDEX_1_0,
        {
            "https://didcomm.org/didexchange/1.0",
            "didexchange/1.0",
            "didexchange",
            "did-exchange",
            "didx",
            "didex",
            "rfc23",
            "rfc-23",
            "23",
            "new",
        },
    )
    DIDEX_1_1 = HSProtoSpec(
        DIDEX_1_1,
        {
            "https://didcomm.org/didexchange/1.1",
            "didexchange/1.1",
        },
    )

    @classmethod
    def get(cls, label: Union[str, "HSProto"]) -> Optional["HSProto"]:
        """Get handshake protocol enum for label."""
        if isinstance(label, str):
            for hsp in HSProto:
                if DIDCommPrefix.unqualify(label) == hsp.name or label.lower() in hsp.aka:
                    return hsp

        elif isinstance(label, HSProto):
            return label

        return None

    @property
    def name(self) -> str:
        """Accessor for name."""
        return self.value.name

    @property
    def aka(self) -> Set[str]:
        """Accessor for also-known-as."""
        return self.value.aka


class ServiceOrDIDField(fields.Field):
    """DIDComm Service object or DID string field for Marshmallow."""

    def _serialize(self, value, attr, obj, **kwargs):
        if isinstance(value, Service):
            return value.serialize()
        return value

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, dict):
            return Service.deserialize(value)
        elif isinstance(value, Service):
            return value
        elif isinstance(value, str):
            if not DIDValidation.PATTERN.match(value):
                raise ValidationError(
                    "Service item must be a valid decentralized identifier (DID)"
                )
            return value
        raise ValidationError(
            "Service item must be a valid decentralized identifier (DID) or object"
        )


class InvitationMessage(AgentMessage):
    """Class representing an out of band invitation message."""

    class Meta:
        """InvitationMessage metadata."""

        schema_class = "InvitationMessageSchema"
        message_type = INVITATION

    def __init__(
        self,
        *,
        label: Optional[str] = None,
        image_url: Optional[str] = None,
        handshake_protocols: Optional[Sequence[Text]] = None,
        requests_attach: Optional[Sequence[AttachDecorator]] = None,
        services: Optional[Sequence[Union[Service, Text]]] = None,
        accept: Optional[Sequence[Text]] = None,
        version: str = DEFAULT_VERSION,
        msg_type: Optional[Text] = None,
        goal_code: Optional[Text] = None,
        goal: Optional[Text] = None,
        **kwargs,
    ):
        """Initialize invitation message object.

        Args:
            label (Optional[str]): The label for the invitation.
            image_url (Optional[str]): The URL of an image associated with the invitation.
            handshake_protocols (Optional[Sequence[Text]]): The supported handshake
                protocols.
            requests_attach (Optional[Sequence[AttachDecorator]]): The request
                attachments.
            services (Optional[Sequence[Union[Service, Text]]]): The services associated
                with the invitation.
            accept (Optional[Sequence[Text]]): The accepted protocols.
            version (str): The version of the invitation message.
            msg_type (Optional[Text]): The type of the invitation message.
            goal_code (Optional[Text]): The goal code.
            goal (Optional[Text]): The goal.
            kwargs: Additional keyword arguments.

        """
        super().__init__(_type=msg_type, _version=version, **kwargs)
        self.label = label
        self.image_url = image_url
        self.handshake_protocols = (
            list(handshake_protocols) if handshake_protocols else []
        )
        self.requests_attach = list(requests_attach) if requests_attach else []
        self.services = services
        self.accept = accept
        self.goal_code = goal_code
        self.goal = goal

    @classmethod
    def wrap_message(cls, message: dict) -> AttachDecorator:
        """Convert an aries message to an attachment decorator."""
        return AttachDecorator.data_json(mapping=message, ident="request-0")

    def to_url(self, base_url: Optional[str] = None) -> str:
        """Convert an invitation message to URL format for sharing.

        Returns:
            An invite url

        """
        c_json = self.to_json()
        oob = bytes_to_b64(c_json.encode("ascii"), urlsafe=True, pad=False)
        endpoint = None
        if not base_url:
            for service_item in self.services:
                if isinstance(service_item, Service):
                    endpoint = service_item.service_endpoint
                    break
        result = urljoin(
            (base_url if base_url else endpoint),
            "?oob={}".format(oob),
        )
        return result

    @classmethod
    def from_url(cls, url: str) -> "InvitationMessage":
        """Parse a URL-encoded invitation into an `InvitationMessage` instance.

        Args:
            url: Url to decode

        Returns:
            An `InvitationMessage` object.

        """
        parts = urlparse(url)
        query = parse_qs(parts.query)
        if "oob" in query:
            oob = b64_to_bytes(query["oob"][0], urlsafe=True)
            return cls.from_json(oob)
        return None


class InvitationMessageSchema(AgentMessageSchema):
    """InvitationMessage schema."""

    class Meta:
        """InvitationMessage schema metadata."""

        model_class = InvitationMessage
        unknown = EXCLUDE

    _type = fields.Str(
        data_key="@type",
        required=False,
        metadata={
            "description": "Message type",
            "example": "https://didcomm.org/my-family/1.0/my-message-type",
        },
    )
    label = fields.Str(
        required=False, metadata={"description": "Optional label", "example": "Bob"}
    )
    image_url = fields.URL(
        data_key="imageUrl",
        required=False,
        allow_none=True,
        metadata={
            "description": "Optional image URL for out-of-band invitation",
            "example": "http://192.168.56.101/img/logo.jpg",
        },
    )
    handshake_protocols = fields.List(
        fields.Str(
            metadata={
                "description": "Handshake protocol",
                "example": DIDCommPrefix.qualify_current(HSProto.RFC23.name),
            }
        ),
        required=False,
    )
    accept = fields.List(
        fields.Str(),
        required=False,
        metadata={
            "example": ["didcomm/aip1", "didcomm/aip2;env=rfc19"],
            "description": "List of mime type in order of preference",
        },
    )
    requests_attach = fields.Nested(
        AttachDecoratorSchema,
        required=False,
        many=True,
        data_key="requests~attach",
        metadata={"description": "Optional request attachment"},
    )
    services = fields.List(
        ServiceOrDIDField(
            required=True,
            metadata={
                "description": (
                    "Either a DIDComm service object (as per RFC0067) or a DID string."
                )
            },
        ),
        metadata={
            "example": [
                {
                    "did": "WgWxqztrNooG92RXvxSTWv",
                    "id": "string",
                    "recipientKeys": [
                        "did:key:z6MkpTHR8VNsBxYAAWHut2Geadd9jSwuBV8xRoAnwWsdvktH"
                    ],
                    "routingKeys": [
                        "did:key:z6MkpTHR8VNsBxYAAWHut2Geadd9jSwuBV8xRoAnwWsdvktH"
                    ],
                    "serviceEndpoint": "http://192.168.56.101:8020",
                    "type": "string",
                },
                "did:sov:WgWxqztrNooG92RXvxSTWv",
            ]
        },
    )
    goal_code = fields.Str(
        required=False,
        metadata={
            "description": (
                "A self-attested code the receiver may want to display to the user or"
                " use in automatically deciding what to do with the out-of-band message"
            ),
            "example": "issue-vc",
        },
    )
    goal = fields.Str(
        required=False,
        metadata={
            "description": (
                "A self-attested string that the receiver may want to display to the"
                " user about the context-specific goal of the out-of-band message"
            ),
            "example": "To issue a Faber College Graduate credential",
        },
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate schema fields.

        Args:
            data: The data to validate
            kwargs: Additional keyword arguments
        Raises:
            ValidationError: If any of the fields do not validate

        """
        handshake_protocols = data.get("handshake_protocols")
        requests_attach = data.get("requests_attach")
        if not handshake_protocols and not requests_attach:
            raise ValidationError(
                "Model must include non-empty "
                "handshake_protocols or requests~attach or both"
            )

        # services = data.get("services")
        # if not ((services and len(services) > 0)):
        #     raise ValidationError(
        #         "Model must include non-empty services array"
        #     )
        goal = data.get("goal")
        goal_code = data.get("goal_code")
        if goal and not goal_code:
            raise ValidationError("Model cannot have goal without goal_code")
        if goal_code and not goal:
            raise ValidationError("Model cannot have goal_code without goal")

    @post_dump
    def post_dump(self, data, **kwargs):
        """Post dump hook."""
        if "requests~attach" in data and not data["requests~attach"]:
            del data["requests~attach"]

        return data
