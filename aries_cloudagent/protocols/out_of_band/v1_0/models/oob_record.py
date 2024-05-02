"""Record for out of band invitations."""

import json
from typing import Any, Mapping, Optional, Union

from marshmallow import fields, validate

from .....connections.models.conn_record import ConnRecord
from .....core.profile import ProfileSession
from .....messaging.decorators.service_decorator import (
    ServiceDecorator,
    ServiceDecoratorSchema,
)
from .....messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from .....messaging.valid import UUID4_EXAMPLE
from .....storage.base import BaseStorage
from .....storage.error import StorageNotFoundError
from .....storage.record import StorageRecord
from ..messages.invitation import InvitationMessage, InvitationMessageSchema


class OobRecord(BaseExchangeRecord):
    """Represents an out of band record."""

    class Meta:
        """OobRecord metadata."""

        schema_class = "OobRecordSchema"

    RECORD_TYPE = "oob_record"
    RECORD_TYPE_METADATA = ConnRecord.RECORD_TYPE_METADATA
    RECORD_ID_NAME = "oob_id"
    RECORD_TOPIC = "out_of_band"
    TAG_NAMES = {
        "invi_msg_id",
        "attach_thread_id",
        "our_recipient_key",
        "connection_id",
        "reuse_msg_id",
    }

    STATE_INITIAL = "initial"
    STATE_PREPARE_RESPONSE = "prepare-response"
    STATE_AWAIT_RESPONSE = "await-response"
    STATE_NOT_ACCEPTED = "reuse-not-accepted"
    STATE_ACCEPTED = "reuse-accepted"
    STATE_DONE = "done"

    ROLE_SENDER = "sender"
    ROLE_RECEIVER = "receiver"

    def __init__(
        self,
        *,
        state: str,
        invi_msg_id: str,
        role: str,
        invitation: Union[InvitationMessage, Mapping[str, Any]],
        their_service: Optional[Union[ServiceDecorator, Mapping[str, Any]]] = None,
        connection_id: Optional[str] = None,
        reuse_msg_id: Optional[str] = None,
        oob_id: Optional[str] = None,
        attach_thread_id: Optional[str] = None,
        our_recipient_key: Optional[str] = None,
        our_service: Optional[Union[ServiceDecorator, Mapping[str, Any]]] = None,
        multi_use: bool = False,
        trace: bool = False,
        **kwargs,
    ):
        """Initialize a new OobRecord."""
        super().__init__(oob_id, state, trace=trace, **kwargs)
        self._id = oob_id
        self.state = state
        self.invi_msg_id = invi_msg_id
        self.role = role
        self._invitation = InvitationMessage.serde(invitation)
        self.connection_id = connection_id
        self.reuse_msg_id = reuse_msg_id
        self._their_service = ServiceDecorator.serde(their_service)
        self._our_service = ServiceDecorator.serde(our_service)
        self.attach_thread_id = attach_thread_id
        self.our_recipient_key = our_recipient_key
        self.multi_use = multi_use
        self.trace = trace

    @property
    def oob_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def invitation(self) -> Optional[InvitationMessage]:
        """Accessor; get deserialized view."""
        return None if self._invitation is None else self._invitation.de

    @invitation.setter
    def invitation(self, value):
        """Setter; store de/serialized views."""
        self._invitation = InvitationMessage.serde(value)

    @property
    def our_service(self) -> Optional[ServiceDecorator]:
        """Accessor; get deserialized view."""
        return None if self._our_service is None else self._our_service.de

    @our_service.setter
    def our_service(self, value: Union[ServiceDecorator, Mapping[str, Any]]):
        """Setter; store de/serialized views."""
        self._our_service = ServiceDecorator.serde(value)

    @property
    def their_service(self) -> Optional[ServiceDecorator]:
        """Accessor; get deserialized view."""
        return None if self._their_service is None else self._their_service.de

    @their_service.setter
    def their_service(self, value: Union[ServiceDecorator, Mapping[str, Any]]):
        """Setter; store de/serialized vies."""
        self._their_service = ServiceDecorator.serde(value)

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this invitation."""
        return {
            **{
                prop: getattr(self, prop)
                for prop in (
                    "state",
                    "their_service",
                    "connection_id",
                    "role",
                    "invi_msg_id",
                    "multi_use",
                )
            },
            **{
                prop: getattr(self, f"_{prop}").ser
                for prop in ("invitation", "our_service", "their_service")
                if getattr(self, prop) is not None
            },
        }

    async def delete_record(self, session: ProfileSession):
        """Perform connection record deletion actions.

        Args:
            session (ProfileSession): session

        """
        await super().delete_record(session)

        # Delete metadata
        if self.connection_id:
            storage = session.inject(BaseStorage)
            await storage.delete_all_records(
                self.RECORD_TYPE_METADATA,
                {"connection_id": self.connection_id},
            )

    async def metadata_get(
        self, session: ProfileSession, key: str, default: Any = None
    ) -> Any:
        """Retrieve arbitrary metadata associated with this connection.

        Args:
            session (ProfileSession): session used for storage
            key (str): key identifying metadata
            default (Any): default value to get; type should be a JSON
                compatible value.

        Returns:
            Any: metadata stored by key

        """
        assert self.connection_id
        storage: BaseStorage = session.inject(BaseStorage)
        try:
            record = await storage.find_record(
                self.RECORD_TYPE_METADATA,
                {"key": key, "connection_id": self.connection_id},
            )
            return json.loads(record.value)
        except StorageNotFoundError:
            return default

    async def metadata_set(self, session: ProfileSession, key: str, value: Any):
        """Set arbitrary metadata associated with this connection.

        Args:
            session (ProfileSession): session used for storage
            key (str): key identifying metadata
            value (Any): value to set
        """
        assert self.connection_id
        value = json.dumps(value)
        storage: BaseStorage = session.inject(BaseStorage)
        try:
            record = await storage.find_record(
                self.RECORD_TYPE_METADATA,
                {"key": key, "connection_id": self.connection_id},
            )
            await storage.update_record(record, value, record.tags)
        except StorageNotFoundError:
            record = StorageRecord(
                self.RECORD_TYPE_METADATA,
                value,
                {"key": key, "connection_id": self.connection_id},
            )
            await storage.add_record(record)

    async def metadata_delete(self, session: ProfileSession, key: str):
        """Delete custom metadata associated with this connection.

        Args:
            session (ProfileSession): session used for storage
            key (str): key of metadata to delete
        """
        assert self.connection_id
        storage: BaseStorage = session.inject(BaseStorage)
        try:
            record = await storage.find_record(
                self.RECORD_TYPE_METADATA,
                {"key": key, "connection_id": self.connection_id},
            )
            await storage.delete_record(record)
        except StorageNotFoundError as err:
            raise KeyError(f"{key} not found in connection metadata") from err

    async def metadata_get_all(self, session: ProfileSession) -> dict:
        """Return all custom metadata associated with this connection.

        Args:
            session (ProfileSession): session used for storage

        Returns:
            dict: dictionary representation of all metadata values

        """
        assert self.connection_id
        storage: BaseStorage = session.inject(BaseStorage)
        records = await storage.find_all_records(
            self.RECORD_TYPE_METADATA,
            {"connection_id": self.connection_id},
        )
        return {record.tags["key"]: json.loads(record.value) for record in records}

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class OobRecordSchema(BaseExchangeSchema):
    """Schema to allow serialization/deserialization of invitation records."""

    class Meta:
        """OobRecordSchema metadata."""

        model_class = OobRecord

    oob_id = fields.Str(
        required=True,
        metadata={"description": "Oob record identifier", "example": UUID4_EXAMPLE},
    )
    state = fields.Str(
        required=True,
        validate=validate.OneOf(
            OobRecord.get_attributes_by_prefix("STATE_", walk_mro=True)
        ),
        metadata={
            "description": "Out of band message exchange state",
            "example": OobRecord.STATE_AWAIT_RESPONSE,
        },
    )
    invi_msg_id = fields.Str(
        required=True,
        metadata={
            "description": "Invitation message identifier",
            "example": UUID4_EXAMPLE,
        },
    )
    invitation = fields.Nested(
        InvitationMessageSchema(),
        required=True,
        metadata={"description": "Out of band invitation message"},
    )

    their_service = fields.Nested(ServiceDecoratorSchema(), required=False)

    connection_id = fields.Str(
        required=False,
        metadata={
            "description": "Connection record identifier",
            "example": UUID4_EXAMPLE,
        },
    )

    attach_thread_id = fields.Str(
        required=False,
        metadata={
            "description": "Connection record identifier",
            "example": UUID4_EXAMPLE,
        },
    )

    our_recipient_key = fields.Str(
        required=False,
        metadata={
            "description": "Recipient key used for oob invitation",
            "example": UUID4_EXAMPLE,
        },
    )

    role = fields.Str(
        required=False,
        validate=validate.OneOf(
            OobRecord.get_attributes_by_prefix("ROLE_", walk_mro=False)
        ),
        metadata={"description": "OOB Role", "example": OobRecord.ROLE_RECEIVER},
    )

    multi_use = fields.Boolean(
        required=False,
        metadata={
            "description": "Allow for multiple uses of the oob invitation",
            "example": True,
        },
    )
