"""Routing manager classes for tracking and inspecting routing records."""

import asyncio
import logging
from typing import Sequence

from ....config.logging import get_logger_inst
from ....core.error import BaseError
from ....core.profile import Profile
from ....storage.error import (
    StorageDuplicateError,
    StorageNotFoundError,
)

from .models.route_record import RouteRecord


RECIP_ROUTE_PAUSE = 0.1
RECIP_ROUTE_RETRY = 10


class RoutingManagerError(BaseError):
    """Generic routing error."""


class RouteNotFoundError(RoutingManagerError):
    """Requested route was not found."""


class RoutingManager:
    """Class for handling routing records."""

    RECORD_TYPE = "forward_route"

    def __init__(self, profile: Profile):
        """Initialize a RoutingManager.

        Args:
            profile: The profile instance for this manager
        """
        self._profile = profile
        if not profile:
            raise RoutingManagerError("Missing profile")
        self._logger: logging.Logger = get_logger_inst(
            profile=profile,
            logger_name=__name__,
        )

    async def get_recipient(self, recip_verkey: str) -> RouteRecord:
        """Resolve the recipient for a verkey.

        Args:
            recip_verkey: The verkey ("to") of the incoming Forward message

        Returns:
            The `RouteRecord` associated with this verkey

        """
        if not recip_verkey:
            raise RoutingManagerError("Must pass non-empty recip_verkey")

        i = 0
        record = None
        while not record:
            try:
                self._logger.info(
                    ">>> fetching routing record for verkey: " + recip_verkey
                )
                async with self._profile.session() as session:
                    record = await RouteRecord.retrieve_by_recipient_key(
                        session, recip_verkey
                    )
                self._logger.info(
                    ">>> FOUND routing record for verkey: " + recip_verkey
                )
                return record
            except StorageDuplicateError:
                self._logger.info(
                    ">>> DUPLICATE routing record for verkey: " + recip_verkey
                )
                raise RouteNotFoundError(
                    f"More than one route record found with recipient key: {recip_verkey}"
                )
            except StorageNotFoundError:
                self._logger.info(
                    ">>> NOT FOUND routing record for verkey: " + recip_verkey
                )
                i += 1
                if i > RECIP_ROUTE_RETRY:
                    raise RouteNotFoundError(
                        f"No route found with recipient key: {recip_verkey}"
                    )
                await asyncio.sleep(RECIP_ROUTE_PAUSE)

    async def get_routes(
        self, client_connection_id: str = None, tag_filter: dict = None
    ) -> Sequence[RouteRecord]:
        """Fetch all routes associated with the current connection.

        Args:
            client_connection_id: The ID of the connection record
            tag_filter: An optional dictionary of tag filters

        Returns:
            A sequence of route records found by the query

        """
        # Routing protocol acts only as Server, filter out all client records
        filters = {"role": RouteRecord.ROLE_SERVER}
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

        async with self._profile.session() as session:
            results = await RouteRecord.query(session, tag_filter=filters)

        return results

    async def delete_route_record(self, route: RouteRecord):
        """Remove an existing route record."""
        async with self._profile.session() as session:
            await route.delete_record(session)

    async def create_route_record(
        self,
        client_connection_id: str = None,
        recipient_key: str = None,
        internal_wallet_id: str = None,
    ) -> RouteRecord:
        """Create and store a new RouteRecord.

        Args:
            client_connection_id: The ID of the connection record
            recipient_key: The recipient verkey of the route
            internal_wallet_id: The ID of the wallet record. Used for internal routing

        Returns:
            The new routing record

        """
        if not (client_connection_id or internal_wallet_id):
            raise RoutingManagerError(
                "Either client_connection_id or internal_wallet_id is required"
            )
        if not recipient_key:
            raise RoutingManagerError("Missing recipient_key")
        self._logger.info(">>> creating routing record for verkey: " + recipient_key)
        route = RouteRecord(
            connection_id=client_connection_id,
            wallet_id=internal_wallet_id,
            recipient_key=recipient_key,
        )
        async with self._profile.session() as session:
            await route.save(session, reason="Created new route")
        self._logger.info(">>> CREATED routing record for verkey: " + recipient_key)
        return route
