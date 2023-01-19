"""An invitation content message."""

from collections import namedtuple
from enum import Enum
from re import sub
from typing import Optional, Sequence, Text, Union
from urllib.parse import parse_qs, urljoin, urlparse

from marshmallow import (
    EXCLUDE,
    fields,
    post_dump,
    validates_schema,
    ValidationError,
)

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from .....messaging.valid import DIDValidation
from .....wallet.util import bytes_to_b64, b64_to_bytes

from ....didcomm_prefix import DIDCommPrefix
from ....didexchange.v1_0.message_types import ARIES_PROTOCOL as DIDX_PROTO
from ....connections.v1_0.message_types import ARIES_PROTOCOL as CONN_PROTO

from ..message_types import INVITATION, DEFAULT_VERSION

from .service import Service

HSProtoSpec = namedtuple("HSProtoSpec", "rfc name aka")


class HSProto(Enum):
    """Handshake protocol enum for invitation message."""

    RFC160 = HSProtoSpec(
        160,
        CONN_PROTO,
        {"connection", "connections", "conn", "conns", "rfc160", "160", "old"},
    )
    RFC23 = HSProtoSpec(
        23,
        DIDX_PROTO,
        {"didexchange", "didx", "didex", "rfc23", "23", "new"},
    )

    @classmethod
    def get(cls, label: Union[str, "HSProto"]) -> "HSProto":
        """Get handshake protocol enum for label."""

        if isinstance(label, str):
            for hsp in HSProto:
                if (
                    DIDCommPrefix.unqualify(label) == hsp.name
                    or sub("[^a-zA-Z0-9]+", "", label.lower()) in hsp.aka
                ):
                    return hsp

        elif isinstance(label, HSProto):
            return label

        elif isinstance(label, int):
            for hsp in HSProto:
                if hsp.rfc == label:
                    return hsp

        return None

    @property
    def rfc(self) -> int:
        """Accessor for RFC."""
        return self.value.rfc

    @property
    def name(self) -> str:
        """Accessor for name."""
        return self.value.name

    @property
    def aka(self) -> int:
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
        # _id: str = None,
        *,
        comment: str = None,
        label: str = None,
        image_url: str = None,
        handshake_protocols: Sequence[Text] = None,
        requests_attach: Sequence[AttachDecorator] = None,
        services: Sequence[Union[Service, Text]] = None,
        accept: Optional[Sequence[Text]] = None,
        version: str = DEFAULT_VERSION,
        msg_type: Optional[Text] = None,
        **kwargs,
    ):
        """
        Initialize invitation message object.

        Args:
            requests_attach: request attachments

        """
        # super().__init__(_id=_id, **kwargs)
        super().__init__(_type=msg_type, _version=version, **kwargs)
        self.label = label
        self.image_url = image_url
        self.handshake_protocols = (
            list(handshake_protocols) if handshake_protocols else []
        )
        self.requests_attach = list(requests_attach) if requests_attach else []
        self.services = services
        self.accept = accept

    @classmethod
    def wrap_message(cls, message: dict) -> AttachDecorator:
        """Convert an aries message to an attachment decorator."""
        return AttachDecorator.data_json(mapping=message, ident="request-0")

    def to_url(self, base_url: str = None) -> str:
        """
        Convert an invitation message to URL format for sharing.

        Returns:
            An invite url

        """
        c_json = self.to_json()
        oob = bytes_to_b64(c_json.encode("ascii"), urlsafe=True)
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
        """
        Parse a URL-encoded invitation into an `InvitationMessage` instance.

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
        description="Message type",
        example="https://didcomm.org/my-family/1.0/my-message-type",
    )
    label = fields.Str(required=False, description="Optional label", example="Bob")
    image_url = fields.URL(
        data_key="imageUrl",
        required=False,
        allow_none=True,
        description="Optional image URL for out-of-band invitation",
        example="http://192.168.56.101/img/logo.jpg",
    )
    handshake_protocols = fields.List(
        fields.Str(
            description="Handshake protocol",
            example=DIDCommPrefix.qualify_current(HSProto.RFC23.name),
        ),
        required=False,
    )
    accept = fields.List(
        fields.Str(),
        example=["didcomm/aip1", "didcomm/aip2;env=rfc19"],
        description=("List of mime type in order of preference"),
        required=False,
    )
    requests_attach = fields.Nested(
        AttachDecoratorSchema,
        required=False,
        many=True,
        data_key="requests~attach",
        description="Optional request attachment",
    )
    services = fields.List(
        ServiceOrDIDField(
            required=True,
            description=(
                "Either a DIDComm service object (as per RFC0067) or a DID string."
            ),
        ),
        example=[
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
        ],
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """
        Validate schema fields.

        Args:
            data: The data to validate
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

    @post_dump
    def post_dump(self, data, **kwargs):
        """Post dump hook."""
        if "requests~attach" in data and not data["requests~attach"]:
            del data["requests~attach"]

        return data
