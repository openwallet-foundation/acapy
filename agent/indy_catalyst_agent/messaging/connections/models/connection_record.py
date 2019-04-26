"""Handle connection information interface with non-secrets storage."""

import asyncio
import datetime
import json
import uuid

from typing import Sequence

from marshmallow import fields

from ....admin.service import AdminService
from ..messages.connection_invitation import ConnectionInvitation
from ..messages.connection_request import ConnectionRequest
from ....models.base import BaseModel, BaseModelSchema
from ....service.base import BaseServiceFactory
from ....storage.base import BaseStorage
from ....storage.record import StorageRecord


def time_now() -> str:
    """Timestamp in ISO format."""
    dt = datetime.datetime.utcnow()
    return dt.replace(tzinfo=datetime.timezone.utc).isoformat(" ")


class ConnectionRecord(BaseModel):
    """Represents a single connection."""

    class Meta:
        """ConnectionRecord metadata."""

        schema_class = "ConnectionRecordSchema"
        repr_exclude = ("_admin_timer",)

    RECORD_TYPE = "connection"
    RECORD_TYPE_ACTIVITY = "connection_activity"
    RECORD_TYPE_INVITATION = "connection_invitation"
    RECORD_TYPE_REQUEST = "connection_request"

    DIRECTION_RECEIVED = "received"
    DIRECTION_SENT = "sent"

    INITIATOR_SELF = "self"
    INITIATOR_EXTERNAL = "external"

    STATE_INIT = "init"
    STATE_INVITATION = "invitation"
    STATE_REQUEST = "request"
    STATE_RESPONSE = "response"
    STATE_ACTIVE = "active"
    STATE_ERROR = "error"
    STATE_INACTIVE = "inactive"

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
        created_at: str = None,
        updated_at: str = None,
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
        self.created_at = created_at
        self.updated_at = updated_at
        self._admin_timer = None

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
        ret.update(
            {
                "error_msg": self.error_msg,
                "their_label": self.their_label,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }
        )
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

    async def save(
        self, storage: BaseStorage, svc_factory: BaseServiceFactory = None
    ) -> str:
        """Persist the connection record to storage.

        Args:
            storage: The `BaseStorage` instance to use
        """
        self.updated_at = time_now()
        if not self._id:
            self._id = str(uuid.uuid4())
            self.created_at = self.updated_at
            await storage.add_record(self.storage_record)
        else:
            record = self.storage_record
            await storage.update_record_value(record, record.value)
            await storage.update_record_tags(record, record.tags)
        await self.admin_send_update(storage, svc_factory)
        return self._id

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
            self.RECORD_TYPE_INVITATION,
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
            self.RECORD_TYPE_INVITATION, {"connection_id": self.connection_id}
        ).fetch_single()
        return ConnectionInvitation.from_json(result.value)

    async def attach_request(self, storage: BaseStorage, request: ConnectionRequest):
        """Persist the related connection request to storage.

        Args:
            storage: The `BaseStorage` instance to use
            request: The request to relate to this connection record
        """
        assert self.connection_id
        record = StorageRecord(
            self.RECORD_TYPE_REQUEST,
            request.to_json(),
            {"connection_id": self.connection_id},
        )
        await storage.add_record(record)

    async def retrieve_request(self, storage: BaseStorage) -> ConnectionRequest:
        """Retrieve the related connection invitation.

        Args:
            storage: The `BaseStorage` instance to use
        """
        assert self.connection_id
        result = await storage.search_records(
            self.RECORD_TYPE_REQUEST, {"connection_id": self.connection_id}
        ).fetch_single()
        return ConnectionRequest.from_json(result.value)

    async def delete_record(self, storage: BaseStorage):
        """Remove the connection record.

        Args:
            storage: The `BaseStorage` instance to use
        """
        if self.connection_id:
            await storage.delete_record(self.storage_record)

    async def log_activity(
        self,
        storage: BaseStorage,
        svc_factory: BaseServiceFactory,
        activity_type: str,
        direction: str,
        meta: dict = None,
    ):
        """Log an event against this connection record.

        Args:
            storage: The `BaseStorage` instance to use
            activity_type: The activity type identifier
            direction: The direction of the activity (sent or received)
            meta: Optional metadata for the activity
        """
        assert self.connection_id
        record = StorageRecord(
            self.RECORD_TYPE_ACTIVITY,
            json.dumps({"meta": meta, "time": time_now()}),
            {
                "type": activity_type,
                "direction": direction,
                "connection_id": self.connection_id,
            },
        )
        await storage.add_record(record)
        await self.admin_send_update(storage, svc_factory)

    async def fetch_activity(
        self, storage: BaseStorage, activity_type: str = None, direction: str = None
    ) -> Sequence[dict]:
        """Fetch all activity logs for this connection record.

        Args:
            storage: The `BaseStorage` instance to use
            activity_type: An optional activity type filter
            direction: An optional direction filter
        """
        tag_filter = {"connection_id": self.connection_id}
        if activity_type:
            tag_filter["activity_type"] = activity_type
        if direction:
            tag_filter["direction"] = direction
        records = await storage.search_records(
            self.RECORD_TYPE_ACTIVITY, tag_filter
        ).fetch_all()
        results = [
            dict(id=record.id, **json.loads(record.value), **record.tags)
            for record in records
        ]
        results.sort(key=lambda x: x["time"], reverse=True)
        return results

    async def retrieve_activity(
        self, storage: BaseStorage, activity_id: str
    ) -> Sequence[dict]:
        """Retrieve a single activity record.

        Args:
            storage: The `BaseStorage` instance to use
            activity_id: The ID of the activity entry
        """
        record = await storage.get_record(self.RECORD_TYPE_ACTIVITY, activity_id)
        result = dict(id=record.id, **json.loads(record.value), **record.tags)
        return result

    async def update_activity_meta(
        self,
        storage: BaseStorage,
        svc_factory: BaseServiceFactory,
        activity_id: str,
        meta: dict,
    ) -> Sequence[dict]:
        """Update metadata for an activity entry.

        Args:
            storage: The `BaseStorage` instance to use
            activity_id: The ID of the activity entry
            meta: The metadata stored on the activity
        """
        record = await storage.get_record(self.RECORD_TYPE_ACTIVITY, activity_id)
        value = json.loads(record.value)
        value["meta"] = meta
        await storage.update_record_value(record, json.dumps(value))
        await self.admin_send_update(storage, svc_factory)

    async def admin_delayed_update(
        self, storage: BaseStorage, svc_factory: BaseServiceFactory, delay: float
    ):
        """Wait a specified time before sending a connection update event."""
        if delay:
            await asyncio.sleep(delay)
        record = self.serialize()
        record["activity"] = await self.fetch_activity(storage)
        if svc_factory:
            service: AdminService = await svc_factory.resolve_service("admin")
            if service:
                await service.add_event("connection_update", {"connection": record})

    async def admin_send_update(
        self, storage: BaseStorage, svc_factory: BaseServiceFactory
    ):
        """Send updated connection status to websocket listener."""
        if self._admin_timer:
            self._admin_timer.cancel()
        self._admin_timer = asyncio.ensure_future(
            self.admin_delayed_update(storage, svc_factory, 0.1)
        )

    @property
    def requires_routing(self) -> bool:
        """Accessor to check if routing actions are needed."""
        return self.routing_state in (
            self.ROUTING_STATE_REQUIRED,
            self.ROUTING_STATE_PENDING,
        )

    def __eq__(self, other) -> bool:
        """Comparison between records."""
        if type(other) is type(self):
            return self.value == other.value and self.tags == other.tags
        return False


class ConnectionRecordSchema(BaseModelSchema):
    """Schema to allow serialization/deserialization of connection records."""

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
    created_at = fields.Str(required=False)
    updated_at = fields.Str(required=False)
