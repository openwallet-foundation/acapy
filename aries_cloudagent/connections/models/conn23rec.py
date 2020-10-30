"""Handle connection information interface with non-secrets storage."""

import json

from enum import Enum
from typing import Any, Union

from marshmallow import fields, validate

from ...config.injection_context import InjectionContext
from ...messaging.models.base_record import BaseRecord, BaseRecordSchema
from ...messaging.valid import INDY_DID, INDY_RAW_PUBLIC_KEY, UUIDFour

from ...protocols.out_of_band.v1_0.messages.invitation import InvitationMessage
from ...protocols.didexchange.v1_0.messages.request import Conn23Request
from ...storage.base import BaseStorage
from ...storage.record import StorageRecord


class Conn23Record(BaseRecord):
    """Represents a single pairwise connection under RFC 23 (DID exchange) protocol."""

    class Meta:
        """Conn23Record metadata."""

        schema_class = "Conn23RecordSchema"

    class Role(Enum):
        """RFC 160 (inviter, invitee) = RFC 23 (responder, requester)."""

        REQUESTER = ("invitee", "requester")  # == RFC 160 initiator, RFC 434 receiver
        RESPONDER = ("inviter", "responder")  # == RFC 23 initiator(!), RFC 434 sender

        @property
        def rfc160(self):
            """Return RFC 160 (connection protocol) nomenclature."""
            return self.value[0]

        @property
        def rfc23(self):
            """Return RFC 23 (DID exchange protocol) nomenclature."""
            return self.value[1]

        @classmethod
        def get(cls, label: str):
            """Get role enum for label."""
            for role in Role:
                if label in role.value:
                    return role
            return None

        def flip(self):
            """Return interlocutor role."""
            return (
                Conn23Record.Role.REQUESTER
                if self is Conn23Record.Role.RESPONDER
                else Conn23Record.Role.RESPONDER
            )

        def __eq__(self, other: Union[str, "Role"]) -> bool:
            """Comparison between roles."""
            if isinstance(other, str):
                return self is Role.get(other)

    RECORD_ID_NAME = "connection_id"
    WEBHOOK_TOPIC = "connections_23"
    LOG_STATE_FLAG = "debug.connections"
    CACHE_ENABLED = True
    TAG_NAMES = {"my_did", "their_did", "request_id", "invitation_key"}

    RECORD_TYPE = "conn23"
    RECORD_TYPE_INVITATION = "conn23_invitation"
    RECORD_TYPE_REQUEST = "conn23_request"

    DIRECTION_RECEIVED = "received"
    DIRECTION_SENT = "sent"

    MULTIUSE = "multiuse"

    STATE_START = "start"
    STATE_INVITATION = "invitation"  # requester: received; responder: created/sent
    STATE_REQUEST = "request"  # requester: created/sent; responder: received
    STATE_RESPONSE = "response-sent"  # requester: received; requester: created/sent
    STATE_ABANDONED = "abandoned"
    STATE_COMPLETED = "completed"

    INVITATION_MODE_ONCE = "once"
    INVITATION_MODE_MULTI = "multi"

    ROUTING_STATE_NONE = "none"
    ROUTING_STATE_REQUEST = "request"
    ROUTING_STATE_ACTIVE = "active"
    ROUTING_STATE_ERROR = "error"

    ACCEPT_MANUAL = "manual"
    ACCEPT_AUTO = "auto"

    def __init__(
        self,
        *,
        connection_id: str = None,
        my_did: str = None,
        their_did: str = None,
        their_label: str = None,
        their_role: str = None,
        invitation_key: str = None,
        request_id: str = None,
        state: str = None,
        inbound_connection_id: str = None,
        error_msg: str = None,
        routing_state: str = None,
        accept: str = None,
        invitation_mode: str = None,
        alias: str = None,
        **kwargs,
    ):
        """Initialize a new Conn23Record."""
        super().__init__(connection_id, state or self.STATE_START, **kwargs)
        self.my_did = my_did
        self.their_did = their_did
        self.their_label = their_label
        self.their_role = their_role
        self.invitation_key = invitation_key
        self.request_id = request_id
        self.error_msg = error_msg
        self.inbound_connection_id = inbound_connection_id
        self.routing_state = routing_state or self.ROUTING_STATE_NONE
        self.accept = accept or self.ACCEPT_MANUAL
        self.invitation_mode = invitation_mode or self.INVITATION_MODE_ONCE
        self.alias = alias

    @property
    def connection_id(self) -> str:
        """Accessor for the ID associated with this connection."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties for this connection."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "inbound_connection_id",
                "routing_state",
                "accept",
                "invitation_mode",
                "alias",
                "error_msg",
                "their_label",
                "their_role",
                "state",
            )
        }

    @classmethod
    async def retrieve_by_did(
        cls,
        context: InjectionContext,
        their_did: str = None,
        my_did: str = None,
        my_role: Role = None,
    ) -> "Conn23Record":
        """Retrieve a connection record by target DID.

        Args:
            context: The injection context to use
            their_did: The target DID to filter by
            my_did: One of our DIDs to filter by
            my_role: Filter connections by record owner role
        """
        tag_filter = {}
        if their_did:
            tag_filter["their_did"] = their_did
        if my_did:
            tag_filter["my_did"] = my_did
        post_filter = {}
        if my_role:
            post_filter["their_role"] = my_role.flip().rfc23
        return await cls.retrieve_by_tag_filter(context, tag_filter, post_filter)

    @classmethod
    async def retrieve_by_invitation_key(
        cls,
        context: InjectionContext,
        invitation_key: str,
        my_role: Role,
    ) -> "Conn23Record":
        """Retrieve a connection record by invitation key and interlocuter role.

        Args:
            context: The injection context to use
            invitation_key: The key on the originating invitation
            my_role: Filter by record owner role value
        """
        assert my_role

        tag_filter = {"invitation_key": invitation_key}
        post_filter = {
            "state": cls.STATE_INVITATION,
            "their_role": my_role.flip().rfc23
        }
        return await cls.retrieve_by_tag_filter(context, tag_filter, post_filter)

    @classmethod
    async def retrieve_by_request_id(
        cls, context: InjectionContext, request_id: str
    ) -> "Conn23Record":
        """Retrieve a connection record from our previous request ID.

        Args:
            context: The injection context to use
            request_id: The ID of the originating connection request
        """
        tag_filter = {"request_id": request_id}
        return await cls.retrieve_by_tag_filter(context, tag_filter)

    async def attach_invitation(
        self, context: InjectionContext, invitation: InvitationMessage
    ):
        """Persist the related connection invitation to storage.

        Args:
            context: The injection context to use
            invitation: The invitation to relate to this connection record
        """
        assert self.connection_id
        record = StorageRecord(
            Conn23Record.RECORD_TYPE_INVITATION,
            invitation.to_json(),
            {"connection_id": self.connection_id},
        )
        storage: BaseStorage = await context.inject(BaseStorage)
        await storage.add_record(record)

    async def retrieve_invitation(
        self, context: InjectionContext
    ) -> InvitationMessage:
        """Retrieve the related connection invitation.

        Args:
            context: The injection context to use
        """
        assert self.connection_id
        storage: BaseStorage = await context.inject(BaseStorage)
        result = await storage.search_records(
            Conn23Record.RECORD_TYPE_INVITATION, {"connection_id": self.connection_id}
        ).fetch_single()
        return InvitationMessage.from_json(result.value)

    async def attach_request(
        self, context: InjectionContext, request: Conn23Request
    ):
        """Persist the related connection request to storage.

        Args:
            context: The injection context to use
            request: The request to relate to this connection record
        """
        assert self.connection_id
        record = StorageRecord(
            Conn23Record.RECORD_TYPE_REQUEST,
            request.to_json(),
            {"connection_id": self.connection_id},
        )
        storage: BaseStorage = await context.inject(BaseStorage)
        await storage.add_record(record)

    async def retrieve_request(self, context: InjectionContext) -> Conn23Request:
        """Retrieve the related connection request.

        Args:
            context: The injection context to use
        """
        assert self.connection_id
        storage: BaseStorage = await context.inject(BaseStorage)
        result = await storage.search_records(
            Conn23Record.RECORD_TYPE_REQUEST, {"connection_id": self.connection_id}
        ).fetch_single()
        return Conn23Request.from_json(result.value)

    @property
    def is_ready(self) -> str:
        """Accessor for connection readiness."""
        return self.state in (
            Conn23Record.STATE_COMPLETED,
            Conn23Record.STATE_RESPONSE
        )

    @property
    def is_multiuse_invitation(self) -> bool:
        """Accessor for multi use invitation mode."""
        return self.invitation_mode == self.INVITATION_MODE_MULTI

    async def post_save(self, context: InjectionContext, *args, **kwargs):
        """Perform post-save actions.

        Args:
            context: The injection context to use
        """
        await super().post_save(context, *args, **kwargs)

        # clear cache key set by connection manager
        cache_key = self.cache_key(self.connection_id, "connection_target")
        await self.clear_cached_key(context, cache_key)

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class Conn23RecordSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of connection records."""

    class Meta:
        """Conn23RecordSchema metadata."""

        model_class = Conn23Record

    connection_id = fields.Str(
        required=False, description="Connection identifier", example=UUIDFour.EXAMPLE
    )
    my_did = fields.Str(
        required=False, description="Our DID for connection", **INDY_DID
    )
    their_did = fields.Str(
        required=False, description="Their DID for connection", **INDY_DID
    )
    their_label = fields.Str(
        required=False, description="Their label for connection", example="Bob"
    )
    their_role = fields.Str(
        required=False,
        description="Their assigned role for connection",
        validate=validate.OneOf(
            [label for role in Conn23Record.Role for label in role.value]
        ),
        example=Conn23Record.Role.REQUESTER.rfc23,
    )
    inbound_connection_id = fields.Str(
        required=False,
        description="Inbound routing connection id to use",
        example=UUIDFour.EXAMPLE,
    )
    invitation_key = fields.Str(
        required=False, description="Public key for connection", **INDY_RAW_PUBLIC_KEY
    )
    request_id = fields.Str(
        required=False,
        description="Connection request identifier",
        example=UUIDFour.EXAMPLE,
    )
    routing_state = fields.Str(
        required=False,
        description="Routing state of connection",
        example=Conn23Record.ROUTING_STATE_ACTIVE,
    )
    accept = fields.Str(
        required=False,
        description="Connection acceptance",
        example=Conn23Record.ACCEPT_AUTO,
        validate=validate.OneOf(
            [
                getattr(Conn23Record, a)
                for a in vars(Conn23Record)
                if a.startswith("ACCEPT_")
            ]
        )
    )
    error_msg = fields.Str(
        required=False,
        description="Error message",
        example="No DIDDoc provided; cannot connect to public DID",
    )
    invitation_mode = fields.Str(
        required=False,
        description="Invitation mode",
        example=Conn23Record.INVITATION_MODE_ONCE,
        validate=validate.OneOf(
            [
                getattr(Conn23Record, i)
                for i in vars(Conn23Record)
                if i.startswith("INVITATION_MODE_")
            ]
        )
    )
    alias = fields.Str(
        required=False,
        description="Optional alias to apply to connection for later use",
        example="Bob, providing quotes",
    )
