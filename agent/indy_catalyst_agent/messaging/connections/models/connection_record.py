"""
Handle connection info interface with storage
"""

import json
import uuid

from ..messages.connection_invitation import ConnectionInvitation
from ....storage.base import BaseStorage
from ....storage.record import StorageRecord


class ConnectionRecord:
    """ """

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
        return self._id

    @property
    def storage_record(self) -> StorageRecord:
        """Accessor for a StorageRecord representing this connection"""
        return StorageRecord(
            self.RECORD_TYPE, json.dumps(self.value), self.tags, self.connection_id
        )

    @property
    def value(self) -> dict:
        """Accessor for the JSON record value generated for this connection"""
        ret = self.tags
        ret.update({"error_msg": self.error_msg, "their_label": self.their_label})
        return ret

    @property
    def tags(self) -> dict:
        """Accessor for the record tags generated for this connection"""
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
        """Persist the connection record to storage"""
        if not self._id:
            self._id = str(uuid.uuid4())
            await storage.add_record(self.storage_record)
        else:
            record = self.storage_record
            await storage.update_record_value(record, record.value)
            await storage.update_record_tags(record, record.tags)

    @classmethod
    async def retrieve_by_id(cls, storage: BaseStorage, connection_id: str):
        """Retrieve a connection record by ID"""
        result = await storage.get_record(cls.RECORD_TYPE, connection_id)
        vals = json.loads(result.value)
        if result.tags:
            vals.update(result.tags)
        return ConnectionRecord(connection_id=connection_id, **vals)

    @classmethod
    async def retrieve_by_tag_filter(
        cls, storage: BaseStorage, tag_filter: dict
    ) -> "ConnectionRecord":
        """Retrieve a connection record by tag filter"""
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
        party: str = None,
    ) -> "ConnectionRecord":
        """Retrieve a connection record by target DID"""
        tag_filter = {"their_did": their_did}
        if my_did:
            tag_filter["my_did"] = my_did
        if party:
            tag_filter["party"] = party
        return await cls.retrieve_by_tag_filter(storage, tag_filter)

    @classmethod
    async def retrieve_by_invitation_key(
        cls, storage: BaseStorage, invitation_key: str, initiator: str = None
    ) -> "ConnectionRecord":
        """Retrieve a connection record by invitation key"""
        tag_filter = {"invitation_key": invitation_key, "state": cls.STATE_INVITATION}
        if initiator:
            tag_filter["initiator"] = initiator
        return await cls.retrieve_by_tag_filter(storage, tag_filter)

    @classmethod
    async def retrieve_by_request_id(
        cls, storage: BaseStorage, request_id
    ) -> "ConnectionRecord":
        """Retrieve a connection record from our previous request ID"""
        tag_filter = {"request_id": request_id}
        return await cls.retrieve_by_tag_filter(storage, tag_filter)

    async def attach_invitation(
        self, storage: BaseStorage, invitation: ConnectionInvitation
    ):
        """Persist the related connection invitation to storage"""
        assert self.connection_id
        record = StorageRecord(
            self.RECORD_INVITATION_TYPE,
            invitation.to_json(),
            {"connection_id": self.connection_id},
        )
        await storage.add_record(record)

    async def retrieve_invitation(self, storage: BaseStorage) -> ConnectionInvitation:
        """Retrieve the related connection invitation"""
        assert self.connection_id
        result = await storage.search_records(
            self.RECORD_INVITATION_TYPE, {"connection_id": self.connection_id}
        ).fetch_single()
        return ConnectionInvitation.from_json(result.value)

    @property
    def requires_routing(self) -> bool:
        """Accessor to check if routing actions are needed"""
        return self.routing_state in (
            self.ROUTING_STATE_REQUIRED,
            self.ROUTING_STATE_PENDING,
        )

    def __repr__(self) -> str:
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
