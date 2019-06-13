"""Handle presentation exchange information interface with non-secrets storage."""

import json
import uuid

from typing import Sequence

from marshmallow import fields

from ....config.injection_context import InjectionContext
from ....storage.base import BaseStorage
from ....storage.record import StorageRecord

from ...models.base import BaseModel, BaseModelSchema


class PresentationExchange(BaseModel):
    """Represents a presentation exchange."""

    class Meta:
        """PresentationExchange metadata."""

        schema_class = "PresentationExchangeSchema"

    RECORD_TYPE = "presentation_exchange"

    INITIATOR_SELF = "self"
    INITIATOR_EXTERNAL = "external"

    STATE_REQUEST_SENT = "request_sent"
    STATE_REQUEST_RECEIVED = "request_received"
    STATE_PRESENTATION_SENT = "presentation_sent"
    STATE_PRESENTATION_RECEIVED = "presentation_received"
    STATE_VERIFIED = "verified"

    def __init__(
        self,
        *,
        presentation_exchange_id: str = None,
        connection_id: str = None,
        thread_id: str = None,
        initiator: str = None,
        state: str = None,
        presentation_request: dict = None,
        presentation: dict = None,
        verified: str = None,
        error_msg: str = None,
    ):
        """Initialize a new PresentationExchange."""
        self._id = presentation_exchange_id
        self.connection_id = connection_id
        self.thread_id = thread_id
        self.initiator = initiator
        self.state = state
        self.presentation_request = presentation_request
        self.presentation = presentation
        self.verified = verified
        self.error_msg = error_msg

    @property
    def presentation_exchange_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def storage_record(self) -> StorageRecord:
        """Accessor for a `StorageRecord` representing this presentation exchange."""
        return StorageRecord(
            self.RECORD_TYPE,
            json.dumps(self.value),
            self.tags,
            self.presentation_exchange_id,
        )

    @property
    def value(self) -> dict:
        """Accessor for JSON record value generated for this presentation exchange."""
        result = self.tags
        for prop in ("presentation_request", "presentation", "error_msg"):
            val = getattr(self, prop)
            if val:
                result[prop] = val
        return result

    @property
    def tags(self) -> dict:
        """Accessor for the record tags generated for this presentation exchange."""
        result = {}
        for prop in ("connection_id", "thread_id", "initiator", "state", "verified"):
            val = getattr(self, prop)
            if val:
                result[prop] = val
        return result

    async def save(self, context: InjectionContext):
        """Persist the presentation exchange record to storage.

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
        cls, context: InjectionContext, presentation_exchange_id: str
    ) -> "PresentationExchange":
        """Retrieve a presentation exchange record by ID.

        Args:
            context: The `InjectionContext` instance to use
            presentation_exchange_id: The ID of the presentation exchange record to find
        """
        storage: BaseStorage = await context.inject(BaseStorage)
        result = await storage.get_record(cls.RECORD_TYPE, presentation_exchange_id)
        vals = json.loads(result.value)
        if result.tags:
            vals.update(result.tags)
        return PresentationExchange(
            presentation_exchange_id=presentation_exchange_id, **vals
        )

    @classmethod
    async def retrieve_by_tag_filter(
        cls, context: InjectionContext, tag_filter: dict
    ) -> "PresentationExchange":
        """Retrieve a presentation exchange record by tag filter.

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
        return PresentationExchange(presentation_exchange_id=result.id, **vals)

    @classmethod
    async def query(
        cls, context: InjectionContext, tag_filter: dict = None
    ) -> Sequence["PresentationExchange"]:
        """Query existing presentation exchange records.

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
                PresentationExchange(presentation_exchange_id=record.id, **vals)
            )
        return result

    async def delete_record(self, context: InjectionContext):
        """Remove the presentation exchange record.

        Args:
            context: The `InjectionContext` instance to use
        """
        if self.presentation_exchange_id:
            storage: BaseStorage = await context.inject(BaseStorage)
            await storage.delete_record(self.storage_record)


class PresentationExchangeSchema(BaseModelSchema):
    """Schema for serialization/deserialization of presentation exchange records."""

    class Meta:
        """PresentationExchangeSchema metadata."""

        model_class = PresentationExchange

    presentation_exchange_id = fields.Str(required=False)
    connection_id = fields.Str(required=False)
    thread_id = fields.Str(required=False)
    initiator = fields.Str(required=False)
    state = fields.Str(required=False)
    presentation_request = fields.Dict(required=False)
    presentation = fields.Dict(required=False)
    verified = fields.Str(required=False)
    error_msg = fields.Str(required=False)
