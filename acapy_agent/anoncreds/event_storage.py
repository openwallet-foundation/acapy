"""Event storage manager for anoncreds revocation registry management."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, NamedTuple, Optional, Type

from anoncreds import RevocationRegistryDefinitionPrivate
from uuid_utils import uuid4

from ..core.profile import ProfileSession
from ..messaging.models.base import BaseModel
from ..messaging.util import datetime_to_str
from ..storage.base import BaseStorage
from ..storage.error import StorageNotFoundError
from ..storage.record import StorageRecord
from ..storage.type import (
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
from .retry_utils import (
    calculate_event_expiry_timestamp,
    get_retry_metadata_for_storage,
)

LOGGER = logging.getLogger(__name__)

all_event_types = [
    RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
    RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
    RECORD_TYPE_REV_LIST_CREATE_EVENT,
    RECORD_TYPE_REV_LIST_STORE_EVENT,
    RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
    RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
]


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
    LOGGER.info("Deserializing %s event payload: %s", payload_class.__name__, event_data)
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
        expiry_timestamp: Optional[str] = None,
    ) -> str:
        """Store a request event to the database.

        Args:
            event_type: The type of event (e.g., RECORD_TYPE_REV_REG_DEF_CREATE_EVENT)
            event_data: The event payload data
            correlation_id: Unique identifier to correlate request/response
            request_id: Unique identifier to trace related events across workflow
            options: Additional options for the event
            expiry_timestamp: When this event expires and becomes eligible for recovery

        Returns:
            The storage record ID
        """
        # Add creation timestamp for recovery delay logic
        created_at = datetime_to_str(datetime.now(timezone.utc))

        # If no expiry timestamp provided, calculate default based on recovery delay
        if not expiry_timestamp:
            from .retry_utils import calculate_event_expiry_timestamp

            expiry_timestamp = calculate_event_expiry_timestamp(0)  # First attempt

        record_data = {
            "event_type": event_type,
            "event_data": event_data,
            "correlation_id": correlation_id,
            "request_id": request_id,
            "state": EVENT_STATE_REQUESTED,
            "options": options or {},
            "created_at": created_at,
            "expiry_timestamp": expiry_timestamp,
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
        retry_metadata: Optional[Dict[str, Any]] = None,
        updated_expiry_timestamp: Optional[str] = None,
        updated_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update an event with response information.

        Args:
            event_type: The type of event
            correlation_id: Unique identifier to correlate request/response
            success: Whether the response indicates success
            response_data: Response payload data
            error_msg: Error message if response indicates failure
            retry_metadata: Metadata for retry behavior and classification
            updated_expiry_timestamp: New expiry timestamp for retry scenarios
            updated_options: Updated options dictionary for retry scenarios
        """
        try:
            record = await self.storage.get_record(event_type, correlation_id)
            record_data = json.loads(record.value)

            # Update the record with response information
            record_data["response_success"] = success
            record_data["response_data"] = response_data or {}
            record_data["error_msg"] = error_msg

            # Add retry metadata if provided
            if retry_metadata:
                record_data["retry_metadata"] = retry_metadata

            # Update expiry timestamp and options if provided (for retry scenarios)
            # Determine new state based on success and retry scenario
            if success:
                new_state = EVENT_STATE_RESPONSE_SUCCESS
            elif updated_expiry_timestamp is not None:
                # Failure with retry - update expiry and keep in requested state
                record_data["expiry_timestamp"] = updated_expiry_timestamp
                new_state = EVENT_STATE_REQUESTED
            else:
                # Failure without retry - mark as failed
                new_state = EVENT_STATE_RESPONSE_FAILURE

            if updated_options is not None:
                record_data["options"] = updated_options

            record_data["state"] = new_state

            new_tags = record.tags.copy()
            new_tags["state"] = record_data["state"]

            await self.storage.update_record(record, json.dumps(record_data), new_tags)

            LOGGER.info(
                "Updated event response: %s with correlation_id: %s, success: %s%s%s",
                event_type,
                correlation_id,
                success,
                f", updated_expiry: {updated_expiry_timestamp}"
                if updated_expiry_timestamp
                else "",
                ", updated_options: True" if updated_options else "",
            )

        except StorageNotFoundError:
            LOGGER.warning(
                "Event record not found for update: %s with correlation_id: %s",
                event_type,
                correlation_id,
            )

    async def update_event_for_retry(
        self,
        event_type: str,
        correlation_id: str,
        error_msg: str,
        retry_count: int,
        updated_options: Dict[str, Any],
    ) -> None:
        """Update an event for retry with exponential backoff logic.

        This is a convenience method that handles the common retry scenario by:
        1. Calculating new expiry timestamp based on retry count
        2. Generating retry metadata
        3. Updating the event record in one atomic operation

        Args:
            event_type: The type of event
            correlation_id: Unique identifier to correlate request/response
            error_msg: Error message from the failed attempt
            retry_count: Current retry count (will be used for next attempt)
            updated_options: Updated options dictionary with new retry_count
        """
        # Calculate new expiry timestamp and retry metadata
        new_expiry = calculate_event_expiry_timestamp(retry_count)
        retry_metadata = get_retry_metadata_for_storage(retry_count)

        # Update the event in one atomic operation
        await self.update_event_response(
            event_type=event_type,
            correlation_id=correlation_id,
            success=False,
            response_data=None,
            error_msg=error_msg,
            retry_metadata=retry_metadata,
            updated_expiry_timestamp=new_expiry,
            updated_options=updated_options,
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
        only_expired: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get all in-progress events for recovery.

        Args:
            event_type: Filter by specific event type, or None for all types
            only_expired: If True, only return events past their expiry timestamp

        Returns:
            List of event records that are in-progress
        """
        event_types_to_search = [event_type] if event_type else all_event_types
        in_progress_events = []

        for etype in event_types_to_search:
            try:
                # Search for events that are not completed
                records = await self.storage.find_all_records(
                    type_filter=etype,
                    tag_query={"state": EVENT_STATE_REQUESTED},
                )

                for record in records:
                    record_data = json.loads(record.value)

                    # Apply expiry timestamp filtering if requested
                    if only_expired and "expiry_timestamp" in record_data:
                        from .retry_utils import is_event_expired

                        if not is_event_expired(record_data["expiry_timestamp"]):
                            LOGGER.debug(
                                "Skipping non-expired event %s (expires: %s)",
                                record_data.get("correlation_id", "unknown"),
                                record_data["expiry_timestamp"],
                            )
                            continue  # Skip this event - it hasn't expired yet

                    in_progress_events.append(
                        {
                            "record_id": record.id,
                            "event_type": etype,
                            "correlation_id": record_data.get("correlation_id"),
                            "request_id": record_data.get("request_id"),
                            "event_data": record_data.get("event_data"),
                            "state": record_data.get("state"),
                            "options": record_data.get("options", {}),
                            "created_at": record_data.get("created_at"),
                            "expiry_timestamp": record_data.get("expiry_timestamp"),
                            "response_data": record_data.get("response_data"),
                            "error_msg": record_data.get("error_msg"),
                        }
                    )

            except Exception as e:
                LOGGER.warning(
                    "Error searching for in-progress events of type %s: %s",
                    etype,
                    str(e),
                )

        if in_progress_events:
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
        """Clean up completed events (SUCCESS or FAILURE states) older than specified age.

        Args:
            event_type: Filter by specific event type, or None for all types
            max_age_hours: Maximum age in hours before cleanup (default: 24)

        Returns:
            Number of events cleaned up
        """
        event_types_to_search = [event_type] if event_type else all_event_types
        cleaned_up = 0

        for etype in event_types_to_search:
            try:
                # Search for completed events (SUCCESS and FAILURE states)
                success_records = await self.storage.find_all_records(
                    type_filter=etype,
                    tag_query={"state": EVENT_STATE_RESPONSE_SUCCESS},
                )
                failure_records = await self.storage.find_all_records(
                    type_filter=etype,
                    tag_query={"state": EVENT_STATE_RESPONSE_FAILURE},
                )

                for record in success_records + failure_records:
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
