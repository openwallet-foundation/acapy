"""Handle issuer registration information with non-secrets storage."""

import json
import uuid

from typing import Sequence

from marshmallow import fields

from indy_catalyst_agent.config.injection_context import InjectionContext
from indy_catalyst_agent.messaging.models.base import BaseModel, BaseModelSchema
from indy_catalyst_agent.storage.base import BaseStorage
from indy_catalyst_agent.storage.record import StorageRecord


class IssuerRegistrationState(BaseModel):
    """Represents a issuer registration."""

    class Meta:
        """IssuerRegistrationState metadata."""

        schema_class = "IssuerRegistrationStateSchema"

    RECORD_TYPE = "issuer_registration"

    INITIATOR_SELF = "self"
    INITIATOR_EXTERNAL = "external"

    STATE_REGISTRATION_SENT = "registration_sent"
    STATE_REGISTRATION_RECEIVED = "registration_received"

    def __init__(
        self,
        *,
        issuer_registration_id: str = None,
        connection_id: str = None,
        issuer_registration: dict = None,
        thread_id: str = None,
        initiator: str = None,
        state: str = None,
        error_msg: str = None,
    ):
        """Initialize a new IssuerRegistrationState."""
        self._id = issuer_registration_id
        self.connection_id = connection_id
        self.issuer_registration = issuer_registration
        self.thread_id = thread_id
        self.initiator = initiator
        self.state = state
        self.error_msg = error_msg

    @property
    def issuer_registration_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def storage_record(self) -> StorageRecord:
        """Accessor for a `StorageRecord` representing this issuer registration."""
        return StorageRecord(
            self.RECORD_TYPE,
            json.dumps(self.value),
            self.tags,
            self.issuer_registration_id,
        )

    @property
    def value(self) -> dict:
        """Accessor for the JSON record value generated for this issuer registration."""
        result = self.tags
        for prop in ("issuer_registration", "error_msg"):
            val = getattr(self, prop)
            if val:
                result[prop] = val
        return result

    @property
    def tags(self) -> dict:
        """Accessor for the record tags generated for this issuer registration."""
        result = {}
        for prop in ("connection_id", "thread_id", "initiator", "state"):
            val = getattr(self, prop)
            if val:
                result[prop] = val
        return result

    async def save(self, context: InjectionContext):
        """Persist the issuer registration record to storage.

        Args:
            context: The `InjectionContext` instance to use
        """
        storage: BaseStorage = await context.inject(BaseStorage)
        if not self._id:
            self._id = str(uuid.uuid4())
            await storage.add_record(self.storage_record)
        else:
            record = self.storage_record
            await storage.update_record_value(record, record.value)
            await storage.update_record_tags(record, record.tags)

    @classmethod
    async def retrieve_by_id(
        cls, context: InjectionContext, issuer_registration_id: str
    ) -> "IssuerRegistrationState":
        """Retrieve a issuer registration record by ID.

        Args:
            context: The `InjectionContext` instance to use
            issuer_registration_id: The ID of the issuer registration record to find
        """
        storage: BaseStorage = await context.inject(BaseStorage)
        result = await storage.get_record(cls.RECORD_TYPE, issuer_registration_id)
        vals = json.loads(result.value)
        if result.tags:
            vals.update(result.tags)
        return IssuerRegistrationState(
            issuer_registration_id=issuer_registration_id, **vals
        )

    @classmethod
    async def retrieve_by_tag_filter(
        cls, context: InjectionContext, tag_filter: dict
    ) -> "IssuerRegistrationState":
        """Retrieve a issuer registration record by tag filter.

        Args:
            context: The `InjectionContext` instance to use
            tag_filter: The filter dictionary to apply
        """
        storage: BaseStorage = await context.inject(BaseStorage)
        result = await storage.search_records(
            cls.RECORD_TYPE, tag_filter
        ).fetch_single()
        vals = json.loads(result.value)
        vals.update(result.tags)
        return IssuerRegistrationState(issuer_registration_id=result.id, **vals)

    @classmethod
    async def query(
        cls, context: InjectionContext, tag_filter: dict = None
    ) -> Sequence["IssuerRegistrationState"]:
        """Query existing issuer registration records.

        Args:
            context: The `InjectionContext` instance to use
            tag_filter: An optional dictionary of tag filter clauses
        """
        storage: BaseStorage = await context.inject(BaseStorage)
        found = await storage.search_records(cls.RECORD_TYPE, tag_filter).fetch_all()
        result = []
        for record in found:
            vals = json.loads(record.value)
            vals.update(record.tags)
            result.append(
                IssuerRegistrationState(issuer_registration_id=record.id, **vals)
            )
        return result

    async def delete_record(self, context: InjectionContext):
        """Remove the issuer registration record.

        Args:
            context: The `InjectionContext` instance to use
        """
        if self.issuer_registration_id:
            storage: BaseStorage = await context.inject(BaseStorage)
            await storage.delete_record(self.storage_record)


class IssuerRegistrationStateSchema(BaseModelSchema):
    """Schema to allow serialization/deserialization of issuer registration records."""

    class Meta:
        """IssuerRegistrationStateSchema metadata."""

        model_class = IssuerRegistrationState

    issuer_registration_id = fields.Str(required=False)
    connection_id = fields.Str(required=False)
    issuer_registration = fields.Dict(required=False)
    thread_id = fields.Str(required=False)
    initiator = fields.Str(required=False)
    state = fields.Str(required=False)
    error_msg = fields.Str(required=False)
