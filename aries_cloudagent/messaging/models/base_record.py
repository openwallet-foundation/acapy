"""Classes for BaseStorage-based record management."""

import json
import sys
import uuid

from datetime import datetime
from typing import Any, Mapping, Sequence, Union

from marshmallow import fields

from ...cache.base import BaseCache
from ...config.settings import BaseSettings
from ...core.profile import ProfileSession
from ...storage.base import BaseStorage, StorageDuplicateError, StorageNotFoundError
from ...storage.record import StorageRecord

from .base import BaseModel, BaseModelSchema
from ..responder import BaseResponder
from ..util import datetime_to_str, time_now
from ..valid import INDY_ISO8601_DATETIME


def match_post_filter(
    record: dict,
    post_filter: dict,
    positive: bool = True,
    alt: bool = False,
) -> bool:
    """Determine if a record value matches the post-filter.

    Args:
        record: record to check
        post_filter: filter to apply (empty or None filter matches everything)
        positive: whether matching all filter criteria positively or negatively
        alt: set to match any (positive=True) value or miss all (positive=False)
            values in post_filter
    """
    if not post_filter:
        return True

    if alt:
        return (
            positive
            and all(
                record.get(k) and record.get(k) in alts
                for k, alts in post_filter.items()
            )
        ) or (
            (not positive)
            and all(
                record.get(k) and record.get(k) not in alts
                for k, alts in post_filter.items()
            )
        )

    for k, v in post_filter.items():
        if record.get(k) != v:
            return not positive

    return positive


class BaseRecord(BaseModel):
    """Represents a single storage record."""

    class Meta:
        """BaseRecord metadata."""

    DEFAULT_CACHE_TTL = 60
    RECORD_ID_NAME = "id"
    RECORD_TYPE = None
    WEBHOOK_TOPIC = None
    LOG_STATE_FLAG = None
    TAG_NAMES = {"state"}

    def __init__(
        self,
        id: str = None,
        state: str = None,
        *,
        created_at: Union[str, datetime] = None,
        updated_at: Union[str, datetime] = None,
    ):
        """Initialize a new BaseRecord."""
        if not self.RECORD_TYPE:
            raise TypeError(
                "Cannot instantiate abstract class {} with no RECORD_TYPE".format(
                    self.__class__.__name__
                )
            )
        self._id = id
        self._last_state = state
        self.state = state
        self.created_at = datetime_to_str(created_at)
        self.updated_at = datetime_to_str(updated_at)

    @classmethod
    def from_storage(cls, record_id: str, record: Mapping[str, Any]):
        """Initialize a record from its stored representation.

        Args:
            record_id: The unique record identifier
            record: The stored representation
        """
        record_id_name = cls.RECORD_ID_NAME
        if record_id_name in record:
            raise ValueError(f"Duplicate {record_id_name} inputs; {record}")
        params = dict(**record)
        params[record_id_name] = record_id
        return cls(**params)

    @classmethod
    def get_tag_map(cls) -> Mapping[str, str]:
        """Accessor for the set of defined tags."""
        return {tag.lstrip("~"): tag for tag in cls.TAG_NAMES or ()}

    @property
    def storage_record(self) -> StorageRecord:
        """Accessor for a `StorageRecord` representing this record."""
        return StorageRecord(
            self.RECORD_TYPE, json.dumps(self.value), self.tags, self._id
        )

    @property
    def record_value(self) -> dict:
        """Accessor to define custom properties for the JSON record value."""
        return {}

    @property
    def value(self) -> dict:
        """Accessor for the JSON record value generated for this record."""
        ret = self.strip_tag_prefix(self.tags)
        ret.update({"created_at": self.created_at, "updated_at": self.updated_at})
        ret.update(self.record_value)
        return ret

    @property
    def record_tags(self) -> dict:
        """Accessor to define implementation-specific tags."""
        return {
            tag: getattr(self, prop)
            for (prop, tag) in self.get_tag_map().items()
            if getattr(self, prop) is not None
        }

    @property
    def tags(self) -> dict:
        """Accessor for the record tags generated for this record."""
        tags = self.record_tags
        return tags

    @classmethod
    async def get_cached_key(cls, session: ProfileSession, cache_key: str):
        """Shortcut method to fetch a cached key value.

        Args:
            session: The profile session to use
            cache_key: The unique cache identifier
        """
        if not cache_key:
            return
        cache = session.inject(BaseCache, required=False)
        if cache:
            return await cache.get(cache_key)

    @classmethod
    async def set_cached_key(
        cls, session: ProfileSession, cache_key: str, value: Any, ttl=None
    ):
        """Shortcut method to set a cached key value.

        Args:
            session: The profile session to use
            cache_key: The unique cache identifier
            value: The value to cache
            ttl: The cache ttl
        """
        if not cache_key:
            return
        cache = session.inject(BaseCache, required=False)
        if cache:
            await cache.set(cache_key, value, ttl or cls.DEFAULT_CACHE_TTL)

    @classmethod
    async def clear_cached_key(cls, session: ProfileSession, cache_key: str):
        """Shortcut method to clear a cached key value, if any.

        Args:
            session: The profile session to use
            cache_key: The unique cache identifier
        """
        if not cache_key:
            return
        cache = session.inject(BaseCache, required=False)
        if cache:
            await cache.clear(cache_key)

    @classmethod
    async def retrieve_by_id(
        cls, session: ProfileSession, record_id: str
    ) -> "BaseRecord":
        """Retrieve a stored record by ID.

        Args:
            session: The profile session to use
            record_id: The ID of the record to find
        """
        storage = session.inject(BaseStorage)
        result = await storage.get_record(
            cls.RECORD_TYPE, record_id, {"retrieveTags": False}
        )
        vals = json.loads(result.value)
        return cls.from_storage(record_id, vals)

    @classmethod
    async def retrieve_by_tag_filter(
        cls, session: ProfileSession, tag_filter: dict, post_filter: dict = None
    ) -> "BaseRecord":
        """Retrieve a record by tag filter.

        Args:
            session: The profile session to use
            tag_filter: The filter dictionary to apply
            post_filter: Additional value filters to apply matching positively,
                with sequence values specifying alternatives to match (hit any)
        """
        storage = session.inject(BaseStorage)
        rows = await storage.find_all_records(
            cls.RECORD_TYPE,
            cls.prefix_tag_filter(tag_filter),
            options={"retrieveTags": False},
        )
        found = None
        for record in rows:
            vals = json.loads(record.value)
            if match_post_filter(vals, post_filter, alt=False):
                if found:
                    raise StorageDuplicateError(
                        "Multiple {} records located for {}{}".format(
                            cls.__name__,
                            tag_filter,
                            f", {post_filter}" if post_filter else "",
                        )
                    )
                found = cls.from_storage(record.id, vals)
        if not found:
            raise StorageNotFoundError(
                "{} record not found for {}{}".format(
                    cls.__name__, tag_filter, f", {post_filter}" if post_filter else ""
                )
            )
        return found

    @classmethod
    async def query(
        cls,
        session: ProfileSession,
        tag_filter: dict = None,
        *,
        post_filter_positive: dict = None,
        post_filter_negative: dict = None,
        alt: bool = False,
    ) -> Sequence["BaseRecord"]:
        """Query stored records.

        Args:
            session: The profile session to use
            tag_filter: An optional dictionary of tag filter clauses
            post_filter_positive: Additional value filters to apply matching positively
            post_filter_negative: Additional value filters to apply matching negatively
            alt: set to match any (positive=True) value or miss all (positive=False)
                values in post_filter
        """
        storage = session.inject(BaseStorage)
        rows = await storage.find_all_records(
            cls.RECORD_TYPE,
            cls.prefix_tag_filter(tag_filter),
            options={"retrieveTags": False},
        )
        result = []
        for record in rows:
            vals = json.loads(record.value)
            if match_post_filter(
                vals,
                post_filter_positive,
                positive=True,
                alt=alt,
            ) and match_post_filter(
                vals,
                post_filter_negative,
                positive=False,
                alt=alt,
            ):
                result.append(cls.from_storage(record.id, vals))
        return result

    async def save(
        self,
        session: ProfileSession,
        *,
        reason: str = None,
        log_params: Mapping[str, Any] = None,
        log_override: bool = False,
        webhook: bool = None,
    ) -> str:
        """Persist the record to storage.

        Args:
            session: The profile session to use
            reason: A reason to add to the log
            log_params: Additional parameters to log
            webhook: Flag to override whether the webhook is sent
        """
        new_record = None
        log_reason = reason or ("Updated record" if self._id else "Created record")
        try:
            self.updated_at = time_now()
            storage = session.inject(BaseStorage)
            if self._id:
                record = self.storage_record
                await storage.update_record(record, record.value, record.tags)
                new_record = False
            else:
                self._id = str(uuid.uuid4())
                self.created_at = self.updated_at
                await storage.add_record(self.storage_record)
                new_record = True
        finally:
            params = {self.RECORD_TYPE: self.serialize()}
            if log_params:
                params.update(log_params)
            if new_record is None:
                log_reason = f"FAILED: {log_reason}"
            self.log_state(
                log_reason, params, override=log_override, settings=session.settings
            )

        await self.post_save(session, new_record, self._last_state, webhook)
        self._last_state = self.state

        return self._id

    async def post_save(
        self,
        session: ProfileSession,
        new_record: bool,
        last_state: str,
        webhook: bool = None,
    ):
        """Perform post-save actions.

        Args:
            session: The profile session to use
            new_record: Flag indicating if the record was just created
            last_state: The previous state value
            webhook: Adjust whether the webhook is called
        """
        webhook_topic = self.webhook_topic
        if webhook is None:
            webhook = bool(webhook_topic) and (new_record or (last_state != self.state))
        if webhook:
            await self.send_webhook(
                session, self.webhook_payload, topic=self.webhook_topic
            )

    async def delete_record(self, session: ProfileSession):
        """Remove the stored record.

        Args:
            session: The profile session to use
        """
        if self._id:
            storage = session.inject(BaseStorage)
            await storage.delete_record(self.storage_record)
        # FIXME - update state and send webhook?

    @property
    def webhook_payload(self):
        """Return a JSON-serialized version of the record for the webhook."""
        return self.serialize()

    @property
    def webhook_topic(self):
        """Return the webhook topic value."""
        return self.WEBHOOK_TOPIC

    async def send_webhook(
        self, session: ProfileSession, payload: Any, topic: str = None
    ):
        """Send a standard webhook.

        Args:
            session: The profile session to use
            payload: The webhook payload
            topic: The webhook topic, defaulting to WEBHOOK_TOPIC
        """
        if not payload:
            return
        if not topic:
            topic = self.webhook_topic
            if not topic:
                return
        responder = session.inject(BaseResponder, required=False)
        if responder:
            await responder.send_webhook(topic, payload)

    @classmethod
    def log_state(
        cls,
        msg: str,
        params: dict = None,
        settings: BaseSettings = None,
        override: bool = False,
    ):
        """Print a message with increased visibility (for testing)."""
        if override or (
            cls.LOG_STATE_FLAG and settings and settings.get(cls.LOG_STATE_FLAG)
        ):
            out = msg + "\n"
            if params:
                for k, v in params.items():
                    out += f"    {k}: {v}\n"
            print(out, file=sys.stderr)

    @classmethod
    def strip_tag_prefix(cls, tags: dict):
        """Strip tilde from unencrypted tag names."""
        return (
            {(k[1:] if "~" in k else k): v for (k, v) in tags.items()} if tags else {}
        )

    @classmethod
    def prefix_tag_filter(cls, tag_filter: dict):
        """Prefix unencrypted tags used in the tag filter."""
        ret = None
        if tag_filter:
            tag_map = cls.get_tag_map()
            ret = {}
            for k, v in tag_filter.items():
                if k in ("$or", "$and") and isinstance(v, list):
                    ret[k] = [cls.prefix_tag_filter(clause) for clause in v]
                elif k == "$not" and isinstance(v, dict):
                    ret[k] = cls.prefix_tag_filter(v)
                else:
                    ret[tag_map.get(k, k)] = v
        return ret

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        if type(other) is type(self):
            return self.value == other.value and self.tags == other.tags
        return False


class BaseExchangeRecord(BaseRecord):
    """Represents a base record with event tracing capability."""

    def __init__(
        self,
        id: str = None,
        state: str = None,
        *,
        trace: bool = False,
        **kwargs,
    ):
        """Initialize a new BaseExchangeRecord."""
        super().__init__(id, state, **kwargs)
        self.trace = trace

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        if type(other) is type(self):
            return (
                self.value == other.value
                and self.tags == other.tags
                and self.trace == other.trace
            )
        return False


class BaseRecordSchema(BaseModelSchema):
    """Schema to allow serialization/deserialization of base records."""

    class Meta:
        """BaseRecordSchema metadata."""

        model_class = None

    state = fields.Str(
        required=False, description="Current record state", example="active"
    )
    created_at = fields.Str(
        required=False, description="Time of record creation", **INDY_ISO8601_DATETIME
    )
    updated_at = fields.Str(
        required=False,
        description="Time of last record update",
        **INDY_ISO8601_DATETIME,
    )


class BaseExchangeSchema(BaseRecordSchema):
    """Base schema for exchange records."""

    class Meta:
        """BaseExchangeSchema metadata."""

        model_class = BaseExchangeRecord

    trace = fields.Boolean(
        description="Record trace information, based on agent configuration",
        required=False,
        default=False,
    )
