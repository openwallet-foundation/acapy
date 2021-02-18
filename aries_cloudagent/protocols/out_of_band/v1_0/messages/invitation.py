"""An invitation content message."""

from collections import namedtuple
from enum import Enum
from re import sub
from typing import Sequence, Text, Union
from urllib.parse import parse_qs, urljoin, urlparse

from marshmallow import (
    EXCLUDE,
    fields,
    post_dump,
    pre_load,
    validates_schema,
    ValidationError,
)

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from .....messaging.valid import INDY_DID
from .....wallet.util import bytes_to_b64, b64_to_bytes

from ....didcomm_prefix import DIDCommPrefix
from ....didexchange.v1_0.message_types import ARIES_PROTOCOL as DIDX_PROTO
from ....connections.v1_0.message_types import ARIES_PROTOCOL as CONN_PROTO

from ..message_types import INVITATION

from .service import Service, ServiceSchema

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
        handshake_protocols: Sequence[Text] = None,
        request_attach: Sequence[AttachDecorator] = None,
        # When loading, we sort service in the two lists
        service: Sequence[Union[Service, Text]] = None,
        service_blocks: Sequence[Service] = None,
        service_dids: Sequence[Text] = None,
        **kwargs,
    ):
        """
        Initialize invitation message object.

        Args:
            request_attach: request attachments

        """
        # super().__init__(_id=_id, **kwargs)
        super().__init__(**kwargs)
        self.label = label
        self.handshake_protocols = (
            list(handshake_protocols) if handshake_protocols else []
        )
        self.request_attach = list(request_attach) if request_attach else []

        # In order to accept and validate both string entries and
        # dict block entries, we include both in schema and manipulate
        # data in pre_load and post_dump
        self.service_blocks = list(service_blocks) if service_blocks else []
        self.service_dids = list(service_dids) if service_dids else []

        # In the case of loading, we need to sort
        # the entries into relevant lists for schema validation
        for s in service or []:
            if type(s) is Service:
                self.service_blocks.append(s)
            elif type(s) is str:
                self.service_dids.append(s)

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
        result = urljoin(
            (base_url if base_url else self.service_blocks[0].service_endpoint),
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

    label = fields.Str(required=False, description="Optional label", example="Bob")
    handshake_protocols = fields.List(
        fields.Str(
            description="Handshake protocol",
            example=DIDCommPrefix.qualify_current(HSProto.RFC23.name),
            validate=lambda hsp: (
                DIDCommPrefix.unqualify(hsp) in [p.name for p in HSProto]
            ),
        ),
        required=False,
    )
    request_attach = fields.Nested(
        AttachDecoratorSchema,
        required=False,
        many=True,
        data_key="request~attach",
        description="Optional request attachment",
    )

    service_blocks = fields.Nested(ServiceSchema, many=True)
    service_dids = fields.List(fields.Str(description="Service DID", **INDY_DID))

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
        request_attach = data.get("request_attach")
        if not (
            (handshake_protocols and len(handshake_protocols) > 0)
            or (request_attach and len(request_attach) > 0)
        ):
            raise ValidationError(
                "Model must include non-empty "
                "handshake_protocols or request_attach or both"
            )

        # service = data.get("service")
        # if not ((service and len(service) > 0)):
        #     raise ValidationError(
        #         "Model must include non-empty service array"
        #     )

    @pre_load
    def pre_load(self, data, **kwargs):
        """Pre load hook."""
        data["service_dids"] = []
        data["service_blocks"] = []

        for service_entry in data["service"]:
            if type(service_entry) is str:
                data["service_dids"].append(service_entry)
            if type(service_entry) is dict:
                data["service_blocks"].append(service_entry)

        del data["service"]

        return data

    @post_dump
    def post_dump(self, data, **kwargs):
        """Post dump hook."""
        data["service"] = []

        for service_entry in data["service_dids"]:
            data["service"].append(service_entry)
        for service_entry in data["service_blocks"]:
            data["service"].append(service_entry)

        del data["service_dids"]
        del data["service_blocks"]

        if "request~attach" in data and not data["request~attach"]:
            del data["request~attach"]

        return data
