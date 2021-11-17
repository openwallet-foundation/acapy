"""."""
import logging

from typing import Union, Mapping, Any
from marshmallow import fields

from .....core.profile import ProfileSession
from .....messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from .....messaging.valid import UUIDFour

from ..messages.disclose import Disclose, DiscloseSchema
from ..messages.query import Query, QuerySchema

from . import UNENCRYPTED_TAGS

LOGGER = logging.getLogger(__name__)


class V10DiscoveryExchangeRecord(BaseExchangeRecord):
    """Represents a Discover Feature (0031) exchange record."""

    class Meta:
        """V10DiscoveryExchangeRecord metadata."""

        schema_class = "V10DiscoveryRecordSchema"

    RECORD_TYPE = "discovery_exchange_v10"
    RECORD_ID_NAME = "discovery_exchange_id"
    RECORD_TOPIC = "dicover_feature"
    TAG_NAMES = {"~thread_id"} if UNENCRYPTED_TAGS else {"thread_id"}

    def __init__(
        self,
        *,
        discovery_exchange_id: str = None,
        connection_id: str = None,
        thread_id: str = None,
        parent_thread_id: str = None,
        comment: str = None,
        query: Union[Mapping, Query],
        disclose: Union[Mapping, Disclose],
        **kwargs,
    ):
        super().__init__(discovery_exchange_id, **kwargs)
        self._id = discovery_exchange_id
        self.connection_id = connection_id
        self.thread_id = thread_id
        self.parent_thread_id = parent_thread_id
        self.comment = comment
        self._query = Query.serde(query)
        self.disclose = Query.serde(disclose)

    @property
    def record_id(self) -> str:
        """Accessor for the ID."""
        return self._id

    @property
    def query(self) -> Query:
        """Accessor; get deserialized view."""
        return None if self._query is None else self._query.de

    @property
    def disclose(self) -> Disclose:
        """Accessor; get deserialized view."""
        return None if self.disclose is None else self.disclose.de

    @classmethod
    async def retrieve_by_connection_id(
        cls, session: ProfileSession, connection_id: str
    ) -> "V10DiscoveryExchangeRecord":
        """Retrieve a discovery exchange record by connection."""
        cache_key = f"discover_exchange_ctidx::{connection_id}"
        record_id = await cls.get_cached_key(session, cache_key)
        if record_id:
            record = await cls.retrieve_by_id(session, record_id)
        else:
            record = await cls.retrieve_by_tag_filter(
                session,
                {"connection_id": connection_id},
            )
            await cls.set_cached_key(session, cache_key, record.discovery_exchange_id)
        return record

    @classmethod
    async def retrieve_by_thread_id(
        cls, session: ProfileSession, thread_id: str
    ) -> "V10DiscoveryExchangeRecord":
        """Retrieve a discovery exchange record by thread ID."""
        cache_key = f"discover_exchange_ctidx::{thread_id}"
        record_id = await cls.get_cached_key(session, cache_key)
        if record_id:
            record = await cls.retrieve_by_id(session, record_id)
        else:
            record = await cls.retrieve_by_tag_filter(
                session,
                {"thread_id": thread_id},
            )
            await cls.set_cached_key(session, cache_key, record.discovery_exchange_id)
        return record

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class V10DiscoveryRecordSchema(BaseExchangeSchema):
    """Schema to allow serialization/deserialization of Discover Feature (0031) records"""

    class Meta:
        """V10DiscoveryRecordSchema metadata."""

        model_class = V10DiscoveryExchangeRecord

    discovery_exchange_id = fields.Str(
        required=False,
        description="Credential exchange identifier",
        example=UUIDFour.EXAMPLE,
    )
    connection_id = fields.Str(
        required=False, description="Connection identifier", example=UUIDFour.EXAMPLE
    )
    thread_id = fields.Str(
        required=False, description="Thread identifier", example=UUIDFour.EXAMPLE
    )
    parent_thread_id = fields.Str(
        required=False, description="Parent thread identifier", example=UUIDFour.EXAMPLE
    )
    comment = fields.Str(required=False, description="Comment")
    query = fields.Nested(
        QuerySchema(),
        required=False,
        description="Query message",
    )
    disclose = fields.Nested(
        DiscloseSchema(),
        required=False,
        description="Disclose message",
    )
