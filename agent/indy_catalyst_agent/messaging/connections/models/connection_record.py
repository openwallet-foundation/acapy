"""Handle connection information interface with non-secrets storage."""

import json
import uuid

from typing import Sequence

from marshmallow import fields

from ..messages.connection_invitation import ConnectionInvitation
from ....models.base import BaseModel, BaseModelSchema
from ....storage.base import BaseStorage
from ....storage.record import StorageRecord


class ConnectionRecord(BaseModel):
    """Represents a single connection."""

    class Meta:
        """ConnectionRecord metadata."""

        schema_class = "ConnectionRecordSchema"

    RECORD_TYPE = "connection"
    RECORD_INVITATION_TYPE = "connection_invitation"

    INITIATOR_SELF = "self"
    INITIATOR_EXTERNAL = "external"

    STATE_INIT = "init"
    STATE_INVITATION = "invitation"
    STATE_REQUEST = "request"
    STATE_RESPONSE = "response"
    STATE_ACTIVE = "active"
    STATE_ERROR = "error"

    ROUTING_STATE_NONE = "none"
    ROUTING_STATE_REQUIRED = "required"
    ROUTING_STATE_PENDING = "pending"
    ROUTING_STATE_ACTIVE = "active"

    def __init__(
        self,
        *,
        connection_id: str = None,
        my_did: str = None,
        my_router_did: str = None,
        their_did: str = None,
        their_label: str = None,
        their_role: str = None,
        initiator: str = None,
        invitation_key: str = None,
        request_id: str = None,
        state: str = None,
        routing_state: str = None,
        error_msg: str = None,
    ):
        """Initialize a new ConnectionRecord."""
        self._id = connection_id
        self.my_did = my_did
        self.my_router_did = my_router_did
        self.their_did = their_did
        self.their_label = their_label
        self.their_role = their_role
        self.initiator = initiator
        self.invitation_key = invitation_key
        self.request_id = request_id
        self.state = state or self.STATE_INIT
        self.routing_state = routing_state or self.ROUTING_STATE_NONE
        self.error_msg = error_msg

    @property
    def connection_id(self) -> str:
        """Accessor for the ID associated with this connection."""
        return self._id

    @property
    def storage_record(self) -> StorageRecord:
        """Accessor for a `StorageRecord` representing this connection."""
        return StorageRecord(
            self.RECORD_TYPE, json.dumps(self.value), self.tags, self.connection_id
        )

    @property
    def value(self) -> dict:
        """Accessor for the JSON record value generated for this connection."""
        ret = self.tags
        ret.update({"error_msg": self.error_msg, "their_label": self.their_label})
        return ret

    @property
    def tags(self) -> dict:
        """Accessor for the record tags generated for this connection."""
        result = {}
        for prop in (
            "my_did",
            "my_router_did",
            "their_did",
            "their_role",
            "initiator",
            "invitation_key",
            "request_id",
            "state",
            "routing_state",
        ):
            val = getattr(self, prop)
            if val:
                result[prop] = val
        return result

    async def save(self, storage: BaseStorage):
        """Persist the connection record to storage.

        Args:
            storage: The `BaseStorage` instance to use
        """
        if not self._id:
            self._id = str(uuid.uuid4())
            await storage.add_record(self.storage_record)
        else:
            record = self.storage_record
            await storage.update_record_value(record, record.value)
            await storage.update_record_tags(record, record.tags)

    @classmethod
    async def retrieve_by_id(
        cls, storage: BaseStorage, connection_id: str
    ) -> "ConnectionRecord":
        """Retrieve a connection record by ID.

        Args:
            storage: The `BaseStorage` instance to use
            connection_id: The ID of the connection record to find
        """
        result = await storage.get_record(cls.RECORD_TYPE, connection_id)
        vals = json.loads(result.value)
        if result.tags:
            vals.update(result.tags)
        return ConnectionRecord(connection_id=connection_id, **vals)

    @classmethod
    async def retrieve_by_tag_filter(
        cls, storage: BaseStorage, tag_filter: dict
    ) -> "ConnectionRecord":
        """Retrieve a connection record by tag filter.

        Args:
            storage: The `BaseStorage` instance to use
            tag_filter: The filter dictionary to apply
        """
        result = await storage.search_records(
            cls.RECORD_TYPE, tag_filter
        ).fetch_single()
        vals = json.loads(result.value)
        vals.update(result.tags)
        return ConnectionRecord(connection_id=result.id, **vals)

    @classmethod
    async def retrieve_by_did(
        cls,
        storage: BaseStorage,
        their_did: str = None,
        my_did: str = None,
        initiator: str = None,
    ) -> "ConnectionRecord":
        """Retrieve a connection record by target DID.

        Args:
            storage: The `BaseStorage` instance to use
            their_did: The target DID to filter by
            my_did: One of our DIDs to filter by
            initiator: Filter connections by the initiator value
        """
        tag_filter = {}
        if their_did:
            tag_filter["their_did"] = their_did
        if my_did:
            tag_filter["my_did"] = my_did
        if initiator:
            tag_filter["initiator"] = initiator
        return await cls.retrieve_by_tag_filter(storage, tag_filter)

    @classmethod
    async def retrieve_by_invitation_key(
        cls, storage: BaseStorage, invitation_key: str, initiator: str = None
    ) -> "ConnectionRecord":
        """Retrieve a connection record by invitation key.

        Args:
            storage: The `BaseStorage` instance to use
            invitation_key: The key on the originating invitation
            initiator: Filter by the initiator value
        """
        tag_filter = {"invitation_key": invitation_key, "state": cls.STATE_INVITATION}
        if initiator:
            tag_filter["initiator"] = initiator
        return await cls.retrieve_by_tag_filter(storage, tag_filter)

    @classmethod
    async def retrieve_by_request_id(
        cls, storage: BaseStorage, request_id: str
    ) -> "ConnectionRecord":
        """Retrieve a connection record from our previous request ID.

        Args:
            storage: The `BaseStorage` instance to use
            request_id: The ID of the originating connection request
        """
        tag_filter = {"request_id": request_id}
        return await cls.retrieve_by_tag_filter(storage, tag_filter)

    @classmethod
    async def query(
        cls, storage: BaseStorage, tag_filter: dict = None
    ) -> Sequence["ConnectionRecord"]:
        """Query existing connection records.

        Args:
            tag_filter: An optional dictionary of tag filter clauses
        """
        found = await storage.search_records(cls.RECORD_TYPE, tag_filter).fetch_all()
        result = []
        for record in found:
            vals = json.loads(record.value)
            vals.update(record.tags)
            result.append(ConnectionRecord(connection_id=record.id, **vals))
        return result

    async def attach_invitation(
        self, storage: BaseStorage, invitation: ConnectionInvitation
    ):
        """Persist the related connection invitation to storage.

        Args:
            storage: The `BaseStorage` instance to use
            invitation: The invitation to relate to this connection record
        """
        assert self.connection_id
        record = StorageRecord(
            self.RECORD_INVITATION_TYPE,
            invitation.to_json(),
            {"connection_id": self.connection_id},
        )
        await storage.add_record(record)

    async def retrieve_invitation(self, storage: BaseStorage) -> ConnectionInvitation:
        """Retrieve the related connection invitation.

        Args:
            storage: The `BaseStorage` instance to use
        """
        assert self.connection_id
        result = await storage.search_records(
            self.RECORD_INVITATION_TYPE, {"connection_id": self.connection_id}
        ).fetch_single()
        return ConnectionInvitation.from_json(result.value)

    @property
    def requires_routing(self) -> bool:
        """Accessor to check if routing actions are needed."""
        return self.routing_state in (
            self.ROUTING_STATE_REQUIRED,
            self.ROUTING_STATE_PENDING,
        )


class ConnectionRecordSchema(BaseModelSchema):
    class Meta:
        """ConnectionRecordSchema metadata."""

        model_class = ConnectionRecord

    connection_id = fields.Str(required=False)
    my_did = fields.Str(required=False)
    my_router_did = fields.Str(required=False)
    their_did = fields.Str(required=False)
    their_label = fields.Str(required=False)
    their_role = fields.Str(required=False)
    initiator = fields.Str(required=False)
    invitation_key = fields.Str(required=False)
    request_id = fields.Str(required=False)
    state = fields.Str(required=False)
    routing_state = fields.Str(required=False)
    error_msg = fields.Str(required=False)
