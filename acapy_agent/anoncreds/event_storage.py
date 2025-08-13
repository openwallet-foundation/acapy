"""Event storage manager for anoncreds revocation registry management."""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, NamedTuple, Optional, Type

from anoncreds import RevocationRegistryDefinitionPrivate
from uuid_utils import uuid4

from ..core.profile import ProfileSession
from ..messaging.util import datetime_to_str, str_to_datetime
from ..messaging.models.base import BaseModel
from ..storage.base import BaseStorage
from ..storage.error import StorageNotFoundError
from ..storage.record import StorageRecord
from ..storage.type import (
    EVENT_STATE_COMPLETED,
    EVENT_STATE_REQUESTED,
    EVENT_STATE_RESPONSE_FAILURE,
    EVENT_STATE_RESPONSE_SUCCESS,
    RECORD_TYPE_REV_LIST_CREATE_EVENT,
    RECORD_TYPE_REV_LIST_STORE_EVENT,
    RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
    RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
    RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
    RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
)
from ..utils.classloader import ClassLoader

LOGGER = logging.getLogger(__name__)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for event tracking."""
    return f"CORR_{str(uuid4())[:16].upper()}"


def generate_request_id() -> str:
    """Generate a unique request ID for tracing related events across a workflow."""
    return f"REQ_{str(uuid4())[:8].upper()}"


def serialize_event_payload(payload: Any) -> Dict[str, Any]:
    """Serialize event payload for storage.

    Args:
        payload: Event payload object (usually a NamedTuple)

    Returns:
        Dictionary representation of the payload
    """
    if hasattr(payload, "_asdict"):
        # Handle NamedTuple payloads
        result = payload._asdict()
        # Recursively serialize nested objects
        for key, value in result.items():
            result[key] = _serialize_nested_object(value)
        return result
    elif isinstance(payload, BaseModel):
        # Handle ACA-Py BaseModel objects
        return payload.serialize()
    elif isinstance(payload, RevocationRegistryDefinitionPrivate):
        # Handle RevocationRegistryDefinitionPrivate objects
        return {"_type": "RevocationRegistryDefinitionPrivate", "data": payload.to_dict()}
    elif hasattr(payload, "__dict__"):
        # Handle regular objects
        result = payload.__dict__.copy()
        # Recursively serialize nested objects
        for key, value in result.items():
            result[key] = _serialize_nested_object(value)
        return result
    elif isinstance(payload, dict):
        # Already a dictionary - recursively serialize values
        result = {}
        for key, value in payload.items():
            result[key] = _serialize_nested_object(value)
        return result
    else:
        # Fallback to string representation
        return {"payload": str(payload)}


def _serialize_nested_object(obj: Any) -> Any:
    """Recursively serialize nested objects within the payload.

    Args:
        obj: Object to serialize

    Returns:
        Serialized representation of the object
    """
    if isinstance(obj, BaseModel):
        # Handle ACA-Py BaseModel objects
        return {
            "_type": "BaseModel",
            "_class": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
            "data": obj.serialize(),
        }
    elif isinstance(obj, RevocationRegistryDefinitionPrivate):
        # Handle RevocationRegistryDefinitionPrivate objects
        return {"_type": "RevocationRegistryDefinitionPrivate", "data": obj.to_dict()}
    elif isinstance(obj, list):
        # Handle lists
        return [_serialize_nested_object(item) for item in obj]
    elif isinstance(obj, dict):
        # Handle dictionaries
        return {key: _serialize_nested_object(value) for key, value in obj.items()}
    else:
        # Return as-is for primitive types
        return obj


def deserialize_event_payload[T: BaseModel | NamedTuple](
    event_data: Dict[str, Any], payload_class: Type[T]
) -> T:
    """Deserialize event payload from storage.

    Args:
        event_data: Dictionary representation of the payload
        payload_class: Class to deserialize into

    Returns:
        Instance of the payload class
    """
    # First, recursively deserialize nested objects
    deserialized_data = {}
    for key, value in event_data.items():
        deserialized_data[key] = _deserialize_nested_object(value)

    if issubclass(payload_class, tuple) and hasattr(payload_class, "_fields"):
        # Handle NamedTuple payloads
        return payload_class(**deserialized_data)
    elif issubclass(payload_class, BaseModel):
        # Handle ACA-Py BaseModel objects
        return payload_class.deserialize(deserialized_data)
    else:
        # Handle regular classes
        LOGGER.warning(
            "Deserializing unexpected payload class: %s", payload_class.__name__
        )
        return payload_class(**deserialized_data)  # type: ignore


def _deserialize_nested_object(obj: Any) -> Any:
    """Recursively deserialize nested objects within the payload.

    Args:
        obj: Object to deserialize

    Returns:
        Deserialized object
    """
    if isinstance(obj, dict) and "_type" in obj:
        if obj["_type"] == "BaseModel":
            # Handle ACA-Py BaseModel objects
            model_class = ClassLoader.load_class(obj["_class"])
            return model_class.deserialize(obj["data"])
        elif obj["_type"] == "RevocationRegistryDefinitionPrivate":
            # Handle RevocationRegistryDefinitionPrivate objects
            return RevocationRegistryDefinitionPrivate.load(obj["data"])
    elif isinstance(obj, list):
        # Handle lists
        return [_deserialize_nested_object(item) for item in obj]
    elif isinstance(obj, dict):
        # Handle dictionaries (but not special serialized objects)
        return {key: _deserialize_nested_object(value) for key, value in obj.items()}
    else:
        # Return as-is for primitive types
        return obj


class EventStorageManager:
    """Manages persistence of events for revocation registry management."""

    def __init__(self, session: ProfileSession):
        """Initialize the EventStorageManager.

        Args:
            session: The profile session to use for storage operations
        """
        self.session = session
        self.storage = session.inject(BaseStorage)

    async def store_event_request(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        correlation_id: str,
        request_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a request event to the database.

        Args:
            event_type: The type of event (e.g., RECORD_TYPE_REV_REG_DEF_CREATE_EVENT)
            event_data: The event payload data
            correlation_id: Unique identifier to correlate request/response
            request_id: Unique identifier to trace related events across workflow
            options: Additional options for the event

        Returns:
            The storage record ID
        """
        # Add creation timestamp for recovery delay logic
        created_at = datetime_to_str(datetime.now(timezone.utc))

        record_data = {
            "event_type": event_type,
            "event_data": event_data,
            "correlation_id": correlation_id,
            "request_id": request_id,
            "state": EVENT_STATE_REQUESTED,
            "options": options or {},
            "created_at": created_at,
        }

        # Use correlation_id as the record ID for easy lookup
        tags = {"correlation_id": correlation_id, "state": EVENT_STATE_REQUESTED}
        if request_id:
            tags["request_id"] = request_id

        record = StorageRecord(
            event_type,
            json.dumps(record_data),
            tags=tags,
            id=correlation_id,
        )

        await self.storage.add_record(record)

        LOGGER.info(
            "Stored request event: %s with correlation_id: %s, request_id: %s",
            event_type,
            correlation_id,
            request_id,
        )

        return correlation_id

    async def update_event_response(
        self,
        event_type: str,
        correlation_id: str,
        success: bool,
        response_data: Optional[Dict[str, Any]] = None,
        error_msg: Optional[str] = None,
    ) -> None:
        """Update an event with response information.

        Args:
            event_type: The type of event
            correlation_id: Unique identifier to correlate request/response
            success: Whether the response indicates success
            response_data: Response payload data
            error_msg: Error message if response indicates failure
        """
        try:
            record = await self.storage.get_record(event_type, correlation_id)
            record_data = json.loads(record.value)

            # Update the record with response information
            record_data["response_success"] = success
            record_data["response_data"] = response_data or {}
            record_data["error_msg"] = error_msg
            record_data["state"] = (
                EVENT_STATE_RESPONSE_SUCCESS if success else EVENT_STATE_RESPONSE_FAILURE
            )

            new_tags = record.tags.copy()
            new_tags["state"] = record_data["state"]

            await self.storage.update_record(record, json.dumps(record_data), new_tags)

            LOGGER.info(
                "Updated event response: %s with correlation_id: %s, success: %s",
                event_type,
                correlation_id,
                success,
            )

        except StorageNotFoundError:
            LOGGER.warning(
                "Event record not found for update: %s with correlation_id: %s",
                event_type,
                correlation_id,
            )

    async def mark_event_completed(
        self,
        event_type: str,
        correlation_id: str,
    ) -> None:
        """Mark an event as completed and ready for cleanup.

        Args:
            event_type: The type of event
            correlation_id: Unique identifier to correlate request/response
        """
        try:
            record = await self.storage.get_record(event_type, correlation_id)
            record_data = json.loads(record.value)

            # Update the record state to completed
            record_data["state"] = EVENT_STATE_COMPLETED

            new_tags = record.tags.copy()
            new_tags["state"] = EVENT_STATE_COMPLETED

            await self.storage.update_record(record, json.dumps(record_data), new_tags)

            LOGGER.info(
                "Marked event completed: %s with correlation_id: %s",
                event_type,
                correlation_id,
            )

        except StorageNotFoundError:
            LOGGER.warning(
                "Event record not found for completion: %s with correlation_id: %s",
                event_type,
                correlation_id,
            )

    async def delete_event(
        self,
        event_type: str,
        correlation_id: str,
    ) -> None:
        """Delete an event record from storage.

        Args:
            event_type: The type of event
            correlation_id: Unique identifier to correlate request/response
        """
        try:
            record = await self.storage.get_record(event_type, correlation_id)
            await self.storage.delete_record(record)

            LOGGER.info(
                "Deleted event: %s with correlation_id: %s",
                event_type,
                correlation_id,
            )

        except StorageNotFoundError:
            LOGGER.warning(
                "Event record not found for deletion: %s with correlation_id: %s",
                event_type,
                correlation_id,
            )

    async def get_in_progress_events(
        self,
        event_type: Optional[str] = None,
        min_age_seconds: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get all in-progress events for recovery.

        Args:
            event_type: Filter by specific event type, or None for all types
            min_age_seconds: Only return events older than this many seconds

        Returns:
            List of event records that are in progress and older than min_age_seconds
        """
        all_event_types = [
            RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
            RECORD_TYPE_REV_LIST_CREATE_EVENT,
            RECORD_TYPE_REV_LIST_STORE_EVENT,
            RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
            RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
        ]

        event_types_to_search = [event_type] if event_type else all_event_types
        in_progress_events = []

        # Calculate cutoff time for recovery delay filtering
        cutoff_time = None
        if min_age_seconds is not None:
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=min_age_seconds)

        for etype in event_types_to_search:
            try:
                # Search for events that are not completed
                records = await self.storage.find_all_records(
                    type_filter=etype,
                    tag_query={"state": EVENT_STATE_REQUESTED},
                )

                for record in records:
                    record_data = json.loads(record.value)

                    # Apply recovery delay filtering if specified
                    if cutoff_time and "created_at" in record_data:
                        try:
                            event_created_at = str_to_datetime(record_data["created_at"])
                            if event_created_at > cutoff_time:
                                LOGGER.debug(
                                    "Skipping recent event %s (created: %s, cutoff: %s)",
                                    record_data["correlation_id"],
                                    record_data["created_at"],
                                    datetime_to_str(cutoff_time),
                                )
                                continue  # Skip this event - it's too recent
                        except (ValueError, KeyError) as e:
                            LOGGER.warning(
                                "Failed to parse created_at for event %s: %s",
                                record_data.get("correlation_id", "unknown"),
                                str(e),
                            )
                            # For events without valid timestamps, recover them

                    in_progress_events.append(
                        {
                            "record_id": record.id,
                            "event_type": etype,
                            "correlation_id": record_data["correlation_id"],
                            "event_data": record_data["event_data"],
                            "state": record_data["state"],
                            "options": record_data.get("options", {}),
                            "created_at": record_data.get("created_at"),
                        }
                    )

            except Exception as e:
                LOGGER.warning(
                    "Error searching for in-progress events of type %s: %s",
                    etype,
                    str(e),
                )

        LOGGER.info(
            "Found %d in-progress events%s",
            len(in_progress_events),
            f" of type {event_type}" if event_type else "",
        )

        return in_progress_events

    async def get_failed_events(
        self,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all failed events for retry or cleanup.

        Args:
            event_type: Filter by specific event type, or None for all types

        Returns:
            List of event records that failed
        """
        all_event_types = [
            RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
            RECORD_TYPE_REV_LIST_CREATE_EVENT,
            RECORD_TYPE_REV_LIST_STORE_EVENT,
            RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
            RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
        ]

        event_types_to_search = [event_type] if event_type else all_event_types
        failed_events = []

        for etype in event_types_to_search:
            try:
                # Search for events that failed
                records = await self.storage.find_all_records(
                    type_filter=etype,
                    tag_query={"state": EVENT_STATE_RESPONSE_FAILURE},
                )

                for record in records:
                    record_data = json.loads(record.value)
                    failed_events.append(
                        {
                            "record_id": record.id,
                            "event_type": etype,
                            "correlation_id": record_data["correlation_id"],
                            "event_data": record_data["event_data"],
                            "state": record_data["state"],
                            "error_msg": record_data.get("error_msg"),
                            "options": record_data.get("options", {}),
                        }
                    )

            except Exception as e:
                LOGGER.warning(
                    "Error searching for failed events of type %s: %s",
                    etype,
                    str(e),
                )

        LOGGER.info(
            "Found %d failed events%s",
            len(failed_events),
            f" of type {event_type}" if event_type else "",
        )

        return failed_events

    async def cleanup_completed_events(
        self,
        event_type: Optional[str] = None,
        max_age_hours: int = 24,
    ) -> int:
        """Clean up completed events older than specified age.

        Args:
            event_type: Filter by specific event type, or None for all types
            max_age_hours: Maximum age in hours before cleanup (default: 24)

        Returns:
            Number of events cleaned up
        """
        all_event_types = [
            RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
            RECORD_TYPE_REV_LIST_CREATE_EVENT,
            RECORD_TYPE_REV_LIST_STORE_EVENT,
            RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
            RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
        ]

        event_types_to_search = [event_type] if event_type else all_event_types
        cleaned_up = 0

        for etype in event_types_to_search:
            try:
                # Search for completed events
                records = await self.storage.find_all_records(
                    type_filter=etype,
                    tag_query={"state": EVENT_STATE_COMPLETED},
                )

                for record in records:
                    # TODO: Add timestamp-based cleanup logic
                    # For now, we'll clean up all completed events
                    await self.storage.delete_record(record)
                    cleaned_up += 1

            except Exception as e:
                LOGGER.warning(
                    "Error cleaning up completed events of type %s: %s",
                    etype,
                    str(e),
                )

        if cleaned_up > 0:
            LOGGER.info(
                "Cleaned up %d completed events%s",
                cleaned_up,
                f" of type {event_type}" if event_type else "",
            )

        return cleaned_up
