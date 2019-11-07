"""Routing manager classes for tracking and inspecting routing records."""

import json
from typing import Sequence

from ...config.injection_context import InjectionContext
from ...error import BaseError
from ...messaging.util import time_now
from ...storage.base import BaseStorage, StorageRecord
from ...storage.error import StorageError, StorageDuplicateError, StorageNotFoundError

from .messages.route_update_request import RouteUpdateRequest
from .models.route_record import RouteRecord
from .models.route_update import RouteUpdate
from .models.route_updated import RouteUpdated


class RoutingManagerError(BaseError):
    """Generic routing error."""


class RouteNotFoundError(RoutingManagerError):
    """Requested route was not found."""


class RoutingManager:
    """Class for handling routing records."""

    RECORD_TYPE = "forward_route"

    def __init__(self, context: InjectionContext):
        """
        Initialize a RoutingManager.

        Args:
            context: The context for this manager
        """
        self._context = context
        if not context:
            raise RoutingManagerError("Missing request context")

    @property
    def context(self) -> InjectionContext:
        """
        Accessor for the current request context.

        Returns:
            The request context for this connection

        """
        return self._context

    async def get_recipient(self, recip_verkey: str) -> RouteRecord:
        """
        Resolve the recipient for a verkey.

        Args:
            recip_verkey: The verkey ("to") of the incoming Forward message

        Returns:
            The `RouteRecord` associated with this verkey

        """
        storage: BaseStorage = await self._context.inject(BaseStorage)
        try:
            record = await storage.search_records(
                self.RECORD_TYPE, {"recipient_key": recip_verkey}
            ).fetch_single()
        except StorageDuplicateError:
            raise RouteNotFoundError(
                "Duplicate routes found for verkey: %s", recip_verkey
            )
        except StorageNotFoundError:
            raise RouteNotFoundError("No route defined for verkey: %s", recip_verkey)
        value = json.loads(record.value)
        return RouteRecord(
            record_id=record.id,
            connection_id=record.tags["connection_id"],
            recipient_key=record.tags["recipient_key"],
            created_at=value.get("created_at"),
            updated_at=value.get("updated_at"),
        )

    async def get_routes(
        self, client_connection_id: str = None, tag_filter: dict = None
    ) -> Sequence[RouteRecord]:
        """
        Fetch all routes associated with the current connection.

        Args:
            client_connection_id: The ID of the connection record
            tag_filter: An optional dictionary of tag filters

        Returns:
            A sequence of route records found by the query

        """
        filters = {}
        if client_connection_id:
            filters["connection_id"] = client_connection_id
        if tag_filter:
            for key in ("recipient_key",):
                if key not in tag_filter:
                    continue
                val = tag_filter[key]
                if isinstance(val, str):
                    filters[key] = val
                elif isinstance(val, list):
                    filters[key] = {"$in": val}
                else:
                    raise RoutingManagerError(
                        "Unsupported tag filter: '{}' = {}".format(key, val)
                    )

        results = []
        storage: BaseStorage = await self._context.inject(BaseStorage)
        async for record in storage.search_records(self.RECORD_TYPE, filters):
            value = json.loads(record.value)
            value.update(record.tags)
            results.append(RouteRecord(**value))
        return results

    async def create_route_record(
        self, client_connection_id: str = None, recipient_key: str = None
    ) -> RouteRecord:
        """
        Create and store a new RouteRecord.

        Args:
            client_connection_id: The ID of the connection record
            recipient_key: The recipient verkey of the route

        Returns:
            The new routing record

        """
        if not client_connection_id:
            raise RoutingManagerError("Missing client_connection_id")
        if not recipient_key:
            raise RoutingManagerError("Missing recipient_key")
        value = {"created_at": time_now(), "updated_at": time_now()}
        record = StorageRecord(
            self.RECORD_TYPE,
            json.dumps(value),
            {"connection_id": client_connection_id, "recipient_key": recipient_key},
        )
        storage: BaseStorage = await self._context.inject(BaseStorage)
        await storage.add_record(record)
        result = RouteRecord(
            record_id=record.id,
            connection_id=client_connection_id,
            recipient_key=recipient_key,
            created_at=value["created_at"],
            updated_at=value["updated_at"],
        )
        return result

    async def delete_route_record(self, route: RouteRecord):
        """Remove an existing route record."""
        if route and route.record_id:
            storage: BaseStorage = await self._context.inject(BaseStorage)
            await storage.delete_record(
                StorageRecord(None, None, None, route.record_id)
            )

    async def update_routes(
        self, client_connection_id: str, updates: Sequence[RouteUpdate]
    ) -> Sequence[RouteUpdated]:
        """
        Update routes associated with the current connection.

        Args:
            client_connection_id: The ID of the connection record
            updates: The sequence of route updates (create/delete) to perform.

        """
        exist_routes = await self.get_routes(client_connection_id)
        exist = {}
        for route in exist_routes:
            exist[route.recipient_key] = route

        updated = []
        for update in updates:
            result = RouteUpdated(
                recipient_key=update.recipient_key, action=update.action
            )
            recip_key = update.recipient_key
            if not recip_key:
                result.result = result.RESULT_CLIENT_ERROR
            elif update.action == update.ACTION_CREATE:
                if recip_key in exist:
                    result.result = result.RESULT_NO_CHANGE
                else:
                    try:
                        await self.create_route_record(client_connection_id, recip_key)
                    except RoutingManagerError:
                        result.result = result.RESULT_SERVER_ERROR
                    else:
                        result.result = result.RESULT_SUCCESS
            elif update.action == update.ACTION_DELETE:
                if recip_key in exist:
                    try:
                        await self.delete_route_record(exist[recip_key])
                    except StorageError:
                        result.result = result.RESULT_SERVER_ERROR
                    else:
                        result.result = result.RESULT_SUCCESS
                else:
                    result.result = result.RESULT_NO_CHANGE
            else:
                result.result = result.RESULT_CLIENT_ERROR
            updated.append(result)
        return updated

    async def send_create_route(
        self, router_connection_id: str, recip_key: str, outbound_handler
    ):
        """Create and send a route update request.

        Returns: the current routing state (request or done)

        """
        msg = RouteUpdateRequest(
            updates=[
                RouteUpdate(recipient_key=recip_key, action=RouteUpdate.ACTION_CREATE)
            ]
        )
        await outbound_handler(msg, connection_id=router_connection_id)
