"""Routing manager classes for tracking and inspecting routing records."""

from typing import Sequence

from ...error import BaseError
from ..request_context import RequestContext
from ...storage.base import StorageRecord
from ...storage.error import StorageNotFoundError


class RoutingManagerError(BaseError):
    """Generic routing error."""


class RoutingManager:
    """Class for handling routing records."""

    RECORD_TYPE = "forward_route"

    def __init__(self, context: RequestContext):
        """
        Initialize a RoutingManager.

        Args:
            context: The context for this manager
        """
        self._context = context
        if not context:
            raise RoutingManagerError("Missing request context")
        if not context.sender_verkey:
            raise RoutingManagerError("Missing sender verkey")

    @property
    def context(self) -> RequestContext:
        """
        Accessor for the current request context.

        Returns:
            The request context for this connection

        """
        return self._context

    async def get_recipient(self, verkey: str) -> str:
        """
        Resolve the recipient for a verkey.

        Returns:
            The verkey associated with the agent which defined this route

        """
        try:
            record = await self._context.storage.get_record(self.RECORD_TYPE, verkey)
        except StorageNotFoundError:
            raise RoutingManagerError("No route defined for verkey: %s", verkey)
        return record.tags["to"]

    async def get_routes(self) -> Sequence[str]:
        """
        Fetch all routes associated with the current connection.

        Returns:
            A sequence of verkeys defined as forwarding routes

        """
        results = []
        async for record in self._context.storage.search_records(
            self.RECORD_TYPE, {"to": self.context.sender_verkey}
        ):
            results.append(record.value)
        return results

    async def create_routes(self, routes: Sequence[str]):
        """Create new routes associated with the current connection.

        Args:
            routes: The sequence of verkeys to create routes for.
        """
        exist_routes = await self.get_routes()
        updates = set(routes) - set(exist_routes)
        for route in updates:
            await self._context.storage.add_record(
                StorageRecord(
                    self.RECORD_TYPE, route, {"to": self.context.sender_verkey}, route
                )
            )

    async def delete_routes(self, routes: Sequence[str]):
        """Remove existing routes associated with the current connection.

        Args:
            routes: The sequence of verkeys to remove from the routes.
        """
        exist_routes = await self.get_routes()
        removes = set(exist_routes).intersection(routes)
        for route in removes:
            await self._context.storage.delete_record(
                StorageRecord(self.RECORD_TYPE, route, id=route)
            )
