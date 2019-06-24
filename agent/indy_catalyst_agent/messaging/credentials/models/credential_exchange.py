"""Handle credential exchange information interface with non-secrets storage."""

import json
import uuid

from typing import Sequence

from marshmallow import fields

from ....cache.base import BaseCache
from ....config.injection_context import InjectionContext
from ....storage.base import BaseStorage
from ....storage.record import StorageRecord

from ...models.base import BaseModel, BaseModelSchema


class CredentialExchange(BaseModel):
    """Represents a credential exchange."""

    class Meta:
        """CredentialExchange metadata."""

        schema_class = "CredentialExchangeSchema"

    RECORD_TYPE = "credential_exchange"

    INITIATOR_SELF = "self"
    INITIATOR_EXTERNAL = "external"

    STATE_OFFER_SENT = "offer_sent"
    STATE_OFFER_RECEIVED = "offer_received"
    STATE_REQUEST_SENT = "request_sent"
    STATE_REQUEST_RECEIVED = "request_received"
    STATE_ISSUED = "issued"
    STATE_STORED = "stored"

    def __init__(
        self,
        *,
        credential_exchange_id: str = None,
        connection_id: str = None,
        thread_id: str = None,
        parent_thread_id: str = None,
        initiator: str = None,
        state: str = None,
        credential_definition_id: str = None,
        schema_id: str = None,
        credential_offer: dict = None,
        credential_request: dict = None,
        credential_request_metadata: dict = None,
        credential_id: str = None,
        credential: dict = None,
        credential_values: dict = None,
        auto_issue: bool = False,
        error_msg: str = None,
    ):
        """Initialize a new CredentialExchange."""
        self._id = credential_exchange_id
        self.connection_id = connection_id
        self.thread_id = thread_id
        self.parent_thread_id = parent_thread_id
        self.initiator = initiator
        self.state = state
        self.credential_definition_id = credential_definition_id
        self.schema_id = schema_id
        self.credential_offer = credential_offer
        self.credential_request = credential_request
        self.credential_request_metadata = credential_request_metadata
        self.credential_id = credential_id
        self.credential = credential
        self.credential_values = credential_values
        self.auto_issue = auto_issue
        self.error_msg = error_msg

    @property
    def credential_exchange_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def storage_record(self) -> StorageRecord:
        """Accessor for a `StorageRecord` representing this credential exchange."""
        return StorageRecord(
            self.RECORD_TYPE,
            json.dumps(self.value),
            self.tags,
            self.credential_exchange_id,
        )

    @property
    def value(self) -> dict:
        """Accessor for the JSON record value generated for this credential exchange."""
        result = self.tags
        for prop in (
            "credential_offer",
            "credential_request",
            "credential_request_metadata",
            "error_msg",
            "auto_issue",
            "credential_values",
            "credential",
            "parent_thread_id",
        ):
            val = getattr(self, prop)
            if val:
                result[prop] = val
        return result

    @property
    def tags(self) -> dict:
        """Accessor for the record tags generated for this credential exchange."""
        result = {}
        for prop in (
            "connection_id",
            "thread_id",
            "initiator",
            "state",
            "credential_definition_id",
            "schema_id",
            "credential_id",
        ):
            val = getattr(self, prop)
            if val:
                result[prop] = val
        return result

    async def save(self, context: InjectionContext):
        """Persist the credential exchange record to storage.

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

        cache_key = f"{self.RECORD_TYPE}::{self._id}"
        cache: BaseCache = await context.inject(BaseCache, required=False)
        if cache:
            await cache.clear(cache_key)

    @classmethod
    async def retrieve_by_id(
        cls, context: InjectionContext, credential_exchange_id: str, cached: bool = True
    ):
        """Retrieve a credential exchange record by ID.

        Args:
            context: The `InjectionContext` instance to use
            credential_exchange_id: The ID of the credential exchange record to find
            cached: Whether to check the cache for this record
        """
        cache = None
        cache_key = f"{cls.RECORD_TYPE}::{credential_exchange_id}"
        vals = None

        if cached and credential_exchange_id:
            cache: BaseCache = await context.inject(BaseCache, required=False)
            if cache:
                vals = await cache.get(cache_key)

        if not vals:
            storage: BaseStorage = await context.inject(BaseStorage)
            result = await storage.get_record(cls.RECORD_TYPE, credential_exchange_id)
            vals = json.loads(result.value)
            if result.tags:
                vals.update(result.tags)
            if cache:
                await cache.set(cache_key, vals, 60)

        return CredentialExchange(credential_exchange_id=credential_exchange_id, **vals)

    @classmethod
    async def retrieve_by_tag_filter(
        cls, context: InjectionContext, tag_filter: dict
    ) -> "CredentialExchange":
        """Retrieve a credential exchange record by tag filter.

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
        return CredentialExchange(credential_exchange_id=result.id, **vals)

    @classmethod
    async def query(
        cls, context: InjectionContext, tag_filter: dict = None
    ) -> Sequence["CredentialExchange"]:
        """Query existing credential exchange records.

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
            result.append(CredentialExchange(credential_exchange_id=record.id, **vals))
        return result

    async def delete_record(self, context: InjectionContext):
        """Remove the credential exchange record.

        Args:
            context: The `InjectionContext` instance to use
        """
        if self.credential_exchange_id:
            storage: BaseStorage = await context.inject(BaseStorage)
            await storage.delete_record(self.storage_record)


class CredentialExchangeSchema(BaseModelSchema):
    """Schema to allow serialization/deserialization of credential exchange records."""

    class Meta:
        """CredentialExchangeSchema metadata."""

        model_class = CredentialExchange

    credential_exchange_id = fields.Str(required=False)
    connection_id = fields.Str(required=False)
    thread_id = fields.Str(required=False)
    parent_thread_id = fields.Str(required=False)
    initiator = fields.Str(required=False)
    state = fields.Str(required=False)
    credential_definition_id = fields.Str(required=False)
    schema_id = fields.Str(required=False)
    credential_offer = fields.Dict(required=False)
    credential_request = fields.Dict(required=False)
    credential_request_metadata = fields.Dict(required=False)
    credential_id = fields.Str(required=False)
    credential = fields.Dict(required=False)
    auto_issue = fields.Bool(required=False)
    credential_values = fields.Dict(required=False)
    error_msg = fields.Str(required=False)
