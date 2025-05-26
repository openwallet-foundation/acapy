"""Multitenancy route manager."""

import logging
from typing import List, Optional

from ..connections.models.conn_record import ConnRecord
from ..core.profile import Profile
from ..messaging.responder import BaseResponder
from ..protocols.coordinate_mediation.v1_0.manager import MediationManager
from ..protocols.coordinate_mediation.v1_0.messages.keylist_update import KeylistUpdate
from ..protocols.coordinate_mediation.v1_0.models.mediation_record import MediationRecord
from ..protocols.coordinate_mediation.v1_0.normalization import (
    normalize_from_did_key,
    normalize_to_did_key,
)
from ..protocols.coordinate_mediation.v1_0.route_manager import (
    CoordinateMediationV1RouteManager,
    RouteManager,
    RoutingInfo,
)
from ..protocols.routing.v1_0.manager import RoutingManager
from ..protocols.routing.v1_0.models.route_record import RouteRecord
from ..storage.error import StorageNotFoundError
from .base import BaseMultitenantManager

LOGGER = logging.getLogger(__name__)


class MultitenantRouteManager(RouteManager):
    """Multitenancy route manager."""

    def __init__(
        self,
        root_profile: Profile,
    ):
        """Initialize multitenant route manager."""
        self.root_profile = root_profile

    async def get_base_wallet_mediator(self) -> Optional[MediationRecord]:
        """Get base wallet's default mediator."""
        return await MediationManager(self.root_profile).get_default_mediator()

    async def _route_for_key(
        self,
        profile: Profile,
        recipient_key: str,
        mediation_record: Optional[MediationRecord] = None,
        *,
        skip_if_exists: bool = False,
        replace_key: Optional[str] = None,
    ) -> Optional[KeylistUpdate]:
        wallet_id = profile.settings["wallet.id"]
        LOGGER.debug(
            "Add route record for recipient %s to wallet %s", recipient_key, wallet_id
        )
        routing_mgr = RoutingManager(self.root_profile)
        mediation_mgr = MediationManager(self.root_profile)
        # If base wallet had mediator, only notify that mediator.
        # Else, if subwallet has mediator, notify that mediator.
        base_mediation_record = await self.get_base_wallet_mediator()
        mediation_record = base_mediation_record or mediation_record

        if skip_if_exists:
            try:
                async with self.root_profile.session() as session:
                    await RouteRecord.retrieve_by_recipient_key(session, recipient_key)

                # If no error is thrown, it means there is already a record
                LOGGER.debug(
                    "Route record already exists for recipient %s to wallet %s. Skipping",
                    recipient_key,
                    wallet_id,
                )
                return None
            except StorageNotFoundError:
                LOGGER.debug(
                    "Route record does not exist for recipient %s to wallet %s. Creating",
                    recipient_key,
                    wallet_id,
                )

        await routing_mgr.create_route_record(
            recipient_key=recipient_key, internal_wallet_id=wallet_id
        )

        # External mediation
        keylist_updates = None
        if mediation_record:
            LOGGER.debug("Adding key to mediation record for recipient %s", recipient_key)
            keylist_updates = await mediation_mgr.add_key(recipient_key)
            if replace_key:
                LOGGER.debug(
                    "Replacing key %s in mediation record %s", replace_key, recipient_key
                )
                keylist_updates = await mediation_mgr.remove_key(
                    replace_key, keylist_updates
                )
            # in order to locate the correct verkey for message packing we need
            # to use the correct profile.
            # if we are using default/base mediation then we need
            # the root_profile to create the responder.
            # if sub-wallets are configuring their own mediation, then
            # we need the sub-wallet (profile) to create the responder.
            profile = self.root_profile if base_mediation_record else profile
            responder = profile.inject(BaseResponder)
            LOGGER.debug(
                "Sending keylist updates to mediator %s", mediation_record.connection_id
            )
            await responder.send(
                keylist_updates, connection_id=mediation_record.connection_id
            )

        return keylist_updates

    async def mediation_records_for_connection(
        self,
        profile: Profile,
        conn_record: ConnRecord,
        mediation_id: Optional[str] = None,
        or_default: bool = False,
    ) -> List[MediationRecord]:
        """Determine mediation records for a connection."""
        conn_specific = await super().mediation_records_for_connection(
            profile, conn_record, mediation_id, or_default
        )
        base_mediation_record = await self.get_base_wallet_mediator()
        return [
            record
            for record in (base_mediation_record, *conn_specific)
            if record is not None
        ]

    async def routing_info(
        self,
        profile: Profile,
        mediation_record: Optional[MediationRecord] = None,
    ) -> RoutingInfo:
        """Return routing info."""
        LOGGER.debug(
            "Getting routing info for profile %s", profile.settings.get("wallet.id", "")
        )
        routing_keys = []

        base_mediation_record = await self.get_base_wallet_mediator()

        my_endpoint = None
        if base_mediation_record:
            routing_keys = base_mediation_record.routing_keys
            my_endpoint = base_mediation_record.endpoint

        if mediation_record:
            routing_keys = [*routing_keys, *mediation_record.routing_keys]
            my_endpoint = mediation_record.endpoint

        routing_keys = [normalize_to_did_key(key).key_id for key in routing_keys] or None

        return RoutingInfo(routing_keys, my_endpoint)


class BaseWalletRouteManager(CoordinateMediationV1RouteManager):
    """Route manager for operations specific to the base wallet."""

    async def connection_from_recipient_key(
        self, profile: Profile, recipient_key: str
    ) -> ConnRecord:
        """Retrieve a connection by recipient key.

        The recipient key is expected to be a local key owned by this agent.

        Since the multi-tenant base wallet can receive and send keylist updates
        for sub wallets, we check the sub wallet's connections before the base
        wallet.
        """
        LOGGER.debug("Retrieving connection for recipient key for multitenant wallet")
        manager = profile.inject(BaseMultitenantManager)
        profile_to_search = (
            await manager.get_profile_for_key(
                profile.context, normalize_from_did_key(recipient_key)
            )
            or profile
        )

        return await super().connection_from_recipient_key(
            profile_to_search, recipient_key
        )
