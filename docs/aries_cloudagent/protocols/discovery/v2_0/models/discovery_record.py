"""."""
import logging
from typing import Any, Mapping, Sequence, Union

from marshmallow import fields

from .....core.profile import ProfileSession
from .....messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from .....messaging.valid import UUID4_EXAMPLE
from .....storage.error import StorageDuplicateError, StorageNotFoundError
from ..messages.disclosures import Disclosures, DisclosuresSchema
from ..messages.queries import Queries, QueriesSchema
from . import UNENCRYPTED_TAGS

LOGGER = logging.getLogger(__name__)


class V20DiscoveryExchangeRecord(BaseExchangeRecord):
    """Represents a Discover Feature v2_0 (0557) exchange record."""

    class Meta:
        """V20DiscoveryExchangeRecord metadata."""

        schema_class = "V20DiscoveryRecordSchema"

    RECORD_TYPE = "discovery_exchange_v20"
    RECORD_ID_NAME = "discovery_exchange_id"
    RECORD_TOPIC = "discover_feature_v2_0"
    TAG_NAMES = {"~thread_id" if UNENCRYPTED_TAGS else "thread_id", "connection_id"}

    def __init__(
        self,
        *,
        discovery_exchange_id: str = None,
        connection_id: str = None,
        thread_id: str = None,
        queries_msg: Union[Sequence, Queries] = None,
        disclosures: Union[Mapping, Disclosures] = None,
        **kwargs,
    ):
        """Initialize a new V20DiscoveryExchangeRecord."""
        super().__init__(discovery_exchange_id, **kwargs)
        self._id = discovery_exchange_id
        self.connection_id = connection_id
        self.thread_id = thread_id
        self._queries_msg = Queries.serde(queries_msg)
        self._disclosures = Disclosures.serde(disclosures)

    @property
    def discovery_exchange_id(self) -> str:
        """Accessor for the ID."""
        return self._id

    @property
    def queries_msg(self) -> Queries:
        """Accessor; get deserialized view."""
        return None if self._queries_msg is None else self._queries_msg.de

    @queries_msg.setter
    def queries_msg(self, value):
        """Setter; store de/serialized views."""
        self._queries_msg = Queries.serde(value)

    @property
    def disclosures(self) -> Disclosures:
        """Accessor; get deserialized view."""
        return None if self._disclosures is None else self._disclosures.de

    @disclosures.setter
    def disclosures(self, value):
        """Setter; store de/serialized views."""
        self._disclosures = Disclosures.serde(value)

    @classmethod
    async def retrieve_by_connection_id(
        cls, session: ProfileSession, connection_id: str
    ) -> "V20DiscoveryExchangeRecord":
        """Retrieve a discovery exchange record by connection."""
        tag_filter = {"connection_id": connection_id}
        return await cls.retrieve_by_tag_filter(session, tag_filter)

    @classmethod
    async def exists_for_connection_id(
        cls, session: ProfileSession, connection_id: str
    ) -> bool:
        """Return whether a discovery exchange record exists for the given connection.

        Args:
            session (ProfileSession): session
            connection_id (str): connection_id

        Returns:
            bool: whether record exists

        """
        tag_filter = {"connection_id": connection_id}
        try:
            record = await cls.retrieve_by_tag_filter(session, tag_filter)
        except StorageNotFoundError:
            return False
        except StorageDuplicateError:
            return True
        return bool(record)

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated."""
        return {
            **{
                prop: getattr(self, f"_{prop}").ser
                for prop in (
                    "queries_msg",
                    "disclosures",
                )
                if getattr(self, prop) is not None
            },
        }

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class V20DiscoveryRecordSchema(BaseExchangeSchema):
    """Schema to allow ser/deser of Discover Feature v2_0 records."""

    class Meta:
        """V20DiscoveryRecordSchema metadata."""

        model_class = V20DiscoveryExchangeRecord

    discovery_exchange_id = fields.Str(
        required=False,
        metadata={
            "description": "Credential exchange identifier",
            "example": UUID4_EXAMPLE,
        },
    )
    connection_id = fields.Str(
        required=False,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )
    thread_id = fields.Str(
        required=False,
        metadata={"description": "Thread identifier", "example": UUID4_EXAMPLE},
    )
    queries_msg = fields.Nested(
        QueriesSchema(), required=False, metadata={"description": "Queries message"}
    )
    disclosures = fields.Nested(
        DisclosuresSchema(),
        required=False,
        metadata={"description": "Disclosures message"},
    )
