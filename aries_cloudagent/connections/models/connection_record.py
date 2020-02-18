"""Handle connection information interface with non-secrets storage."""

from marshmallow import fields
from marshmallow.validate import OneOf

from ...config.injection_context import InjectionContext
from ...messaging.models.base_record import BaseRecord, BaseRecordSchema
from ...messaging.valid import INDY_DID, INDY_RAW_PUBLIC_KEY, UUIDFour
from ...protocols.connections.messages.connection_invitation import ConnectionInvitation
from ...protocols.connections.messages.connection_request import ConnectionRequest
from ...storage.base import BaseStorage
from ...storage.record import StorageRecord


class ConnectionRecord(BaseRecord):  # lgtm[py/missing-equals]
    """Represents a single pairwise connection."""

    class Meta:
        """ConnectionRecord metadata."""

        schema_class = "ConnectionRecordSchema"

    RECORD_ID_NAME = "connection_id"
    WEBHOOK_TOPIC = "connections"
    LOG_STATE_FLAG = "debug.connections"
    CACHE_ENABLED = True
    TAG_NAMES = {
        "my_did",
        "their_did",
        "request_id",
        "invitation_key",
    }

    RECORD_TYPE = "connection"
    RECORD_TYPE_INVITATION = "connection_invitation"
    RECORD_TYPE_REQUEST = "connection_request"

    DIRECTION_RECEIVED = "received"
    DIRECTION_SENT = "sent"

    INITIATOR_SELF = "self"
    INITIATOR_EXTERNAL = "external"
    INITIATOR_MULTIUSE = "multiuse"

    STATE_INIT = "init"
    STATE_INVITATION = "invitation"
    STATE_REQUEST = "request"
    STATE_RESPONSE = "response"
    STATE_ACTIVE = "active"
    STATE_ERROR = "error"
    STATE_INACTIVE = "inactive"

    INVITATION_MODE_ONCE = "once"
    INVITATION_MODE_MULTI = "multi"
    INVITATION_MODE_STATIC = "static"

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
        initiator: str = None,
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
        """Initialize a new ConnectionRecord."""
        super().__init__(connection_id, state or self.STATE_INIT, **kwargs)
        self.my_did = my_did
        self.their_did = their_did
        self.their_label = their_label
        self.their_role = their_role
        self.initiator = initiator
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
                "initiator",
                "their_role",
                "inbound_connection_id",
                "routing_state",
                "accept",
                "invitation_mode",
                "alias",
                "error_msg",
                "their_label",
                "state",
            )
        }

    @classmethod
    async def retrieve_by_did(
        cls,
        context: InjectionContext,
        their_did: str = None,
        my_did: str = None,
        initiator: str = None,
    ) -> "ConnectionRecord":
        """Retrieve a connection record by target DID.

        Args:
            context: The injection context to use
            their_did: The target DID to filter by
            my_did: One of our DIDs to filter by
            initiator: Filter connections by the initiator value
        """
        tag_filter = {}
        if their_did:
            tag_filter["their_did"] = their_did
        if my_did:
            tag_filter["my_did"] = my_did
        post_filter = {}
        if initiator:
            post_filter["initiator"] = initiator
        return await cls.retrieve_by_tag_filter(context, tag_filter, post_filter)

    @classmethod
    async def retrieve_by_invitation_key(
        cls, context: InjectionContext, invitation_key: str, initiator: str = None
    ) -> "ConnectionRecord":
        """Retrieve a connection record by invitation key.

        Args:
            context: The injection context to use
            invitation_key: The key on the originating invitation
            initiator: Filter by the initiator value
        """
        tag_filter = {"invitation_key": invitation_key}
        post_filter = {"state": cls.STATE_INVITATION}
        if initiator:
            post_filter["initiator"] = initiator
        return await cls.retrieve_by_tag_filter(context, tag_filter, post_filter)

    @classmethod
    async def retrieve_by_request_id(
        cls, context: InjectionContext, request_id: str
    ) -> "ConnectionRecord":
        """Retrieve a connection record from our previous request ID.

        Args:
            context: The injection context to use
            request_id: The ID of the originating connection request
        """
        tag_filter = {"request_id": request_id}
        return await cls.retrieve_by_tag_filter(context, tag_filter)

    async def attach_invitation(
        self, context: InjectionContext, invitation: ConnectionInvitation
    ):
        """Persist the related connection invitation to storage.

        Args:
            context: The injection context to use
            invitation: The invitation to relate to this connection record
        """
        assert self.connection_id
        record = StorageRecord(
            self.RECORD_TYPE_INVITATION,
            invitation.to_json(),
            {"connection_id": self.connection_id},
        )
        storage: BaseStorage = await context.inject(BaseStorage)
        await storage.add_record(record)

    async def retrieve_invitation(
        self, context: InjectionContext
    ) -> ConnectionInvitation:
        """Retrieve the related connection invitation.

        Args:
            context: The injection context to use
        """
        assert self.connection_id
        storage: BaseStorage = await context.inject(BaseStorage)
        result = await storage.search_records(
            self.RECORD_TYPE_INVITATION, {"connection_id": self.connection_id}
        ).fetch_single()
        return ConnectionInvitation.from_json(result.value)

    async def attach_request(
        self, context: InjectionContext, request: ConnectionRequest
    ):
        """Persist the related connection request to storage.

        Args:
            context: The injection context to use
            request: The request to relate to this connection record
        """
        assert self.connection_id
        record = StorageRecord(
            self.RECORD_TYPE_REQUEST,
            request.to_json(),
            {"connection_id": self.connection_id},
        )
        storage: BaseStorage = await context.inject(BaseStorage)
        await storage.add_record(record)

    async def retrieve_request(self, context: InjectionContext) -> ConnectionRequest:
        """Retrieve the related connection invitation.

        Args:
            context: The injection context to use
        """
        assert self.connection_id
        storage: BaseStorage = await context.inject(BaseStorage)
        result = await storage.search_records(
            self.RECORD_TYPE_REQUEST, {"connection_id": self.connection_id}
        ).fetch_single()
        return ConnectionRequest.from_json(result.value)

    @property
    def is_ready(self) -> str:
        """Accessor for connection readiness."""
        return self.state == self.STATE_ACTIVE or self.state == self.STATE_RESPONSE

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


class ConnectionRecordSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of connection records."""

    class Meta:
        """ConnectionRecordSchema metadata."""

        model_class = ConnectionRecord

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
        example="Point of contact",
    )
    inbound_connection_id = fields.Str(
        required=False,
        description="Inbound routing connection id to use",
        example=UUIDFour.EXAMPLE,
    )
    initiator = fields.Str(
        required=False,
        description="Connection initiator: self, external, or multiuse",
        example=ConnectionRecord.INITIATOR_SELF,
        validate=OneOf(["self", "external", "multiuse"]),
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
        example=ConnectionRecord.ROUTING_STATE_ACTIVE,
    )
    accept = fields.Str(
        required=False,
        description="Connection acceptance: manual or auto",
        example=ConnectionRecord.ACCEPT_AUTO,
        validate=OneOf(["manual", "auto"]),
    )
    error_msg = fields.Str(
        required=False,
        description="Error message",
        example="No DIDDoc provided; cannot connect to public DID",
    )
    invitation_mode = fields.Str(
        required=False,
        description="Invitation mode: once, multi, or static",
        example=ConnectionRecord.INVITATION_MODE_ONCE,
        validate=OneOf(["once", "multi", "static"]),
    )
    alias = fields.Str(
        required=False,
        description="Optional alias to apply to connection for later use",
        example="Bob, providing quotes",
    )
