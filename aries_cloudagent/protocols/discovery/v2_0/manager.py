"""Classes to manage discover features."""

import asyncio
import logging

from typing import Tuple, Optional, Sequence

from ....core.error import BaseError
from ....core.profile import Profile
from ....core.protocol_registry import ProtocolRegistry
from ....core.goal_code_registry import GoalCodeRegistry
from ....storage.error import StorageNotFoundError
from ....messaging.responder import BaseResponder

from .messages.disclosures import Disclosures
from .messages.queries import QueryItem, Queries
from .models.discovery_record import V20DiscoveryExchangeRecord


class V20DiscoveryMgrError(BaseError):
    """Discover feature v2_0 error."""


class V20DiscoveryMgr:
    """Class for discover feature v1_0 under RFC 31."""

    def __init__(self, profile: Profile):
        """
        Initialize a V20DiscoveryMgr.

        Args:
            profile: The profile for this manager
        """
        self._profile = profile
        self._logger = logging.getLogger(__name__)

    @property
    def profile(self) -> Profile:
        """
        Accessor for the current Profile.

        Returns:
            The Profile for this manager

        """
        return self._profile

    async def receive_disclose(
        self, disclose_msg: Disclosures, connection_id: str = None
    ) -> V20DiscoveryExchangeRecord:
        """Receive Disclose message and return updated V20DiscoveryExchangeRecord."""
        if disclose_msg._thread:
            thread_id = disclose_msg._thread.thid
            try:
                async with self._profile.session() as session:
                    discover_exch_rec = await V20DiscoveryExchangeRecord.retrieve_by_id(
                        session=session, record_id=thread_id
                    )
            except StorageNotFoundError:
                discover_exch_rec = await self.lookup_exchange_rec_by_connection(
                    connection_id
                )
                if not discover_exch_rec:
                    discover_exch_rec = V20DiscoveryExchangeRecord()
        else:
            discover_exch_rec = await self.lookup_exchange_rec_by_connection(
                connection_id
            )
            if not discover_exch_rec:
                discover_exch_rec = V20DiscoveryExchangeRecord()
        async with self._profile.session() as session:
            discover_exch_rec.disclosures = disclose_msg
            discover_exch_rec.connection_id = connection_id
            await discover_exch_rec.save(session)
        return discover_exch_rec

    async def lookup_exchange_rec_by_connection(
        self, connection_id: str
    ) -> Optional[V20DiscoveryExchangeRecord]:
        """Retrieve V20DiscoveryExchangeRecord by connection_id."""
        async with self._profile.session() as session:
            if await V20DiscoveryExchangeRecord.exists_for_connection_id(
                session=session, connection_id=connection_id
            ):
                return await V20DiscoveryExchangeRecord.retrieve_by_connection_id(
                    session=session, connection_id=connection_id
                )
            else:
                return None

    async def proactive_disclose_features(self, connection_id: str):
        """Proactively dislose features on active connection setup."""
        queries_msg = Queries(
            queries=[
                QueryItem(feature_type="protocol", match="*"),
                QueryItem(feature_type="goal-code", match="*"),
            ]
        )
        disclosures = await self.receive_query(queries_msg=queries_msg)
        responder = self.profile.inject_or(BaseResponder)
        if responder:
            await responder.send(disclosures, connection_id=connection_id)
        else:
            self._logger.exception(
                "Unable to send discover-features v2 disclosures message"
                ": BaseResponder unavailable"
            )

    async def return_to_publish_features(
        self,
    ) -> Tuple[Optional[Sequence[str]], Optional[Sequence[str]]]:
        """Return to_publish features filter, if specified."""
        to_publish_protocols = None
        to_publish_goal_codes = None
        async with self._profile.session() as session:
            if (
                session.settings.get("disclose_protocol_list")
                and len(session.settings.get("disclose_protocol_list")) > 0
            ):
                to_publish_protocols = session.settings.get("disclose_protocol_list")
            if (
                session.settings.get("disclose_goal_code_list")
                and len(session.settings.get("disclose_goal_code_list")) > 0
            ):
                to_publish_goal_codes = session.settings.get("disclose_goal_code_list")
        return (to_publish_protocols, to_publish_goal_codes)

    async def execute_protocol_query(self, match: str):
        """Execute protocol match query."""
        protocol_registry = self._profile.context.inject_or(ProtocolRegistry)
        protocols = protocol_registry.protocols_matching_query(match)
        results = await protocol_registry.prepare_disclosed(
            self._profile.context, protocols
        )
        return results

    async def execute_goal_code_query(self, match: str):
        """Execute goal code match query."""
        goal_code_registry = self._profile.context.inject_or(GoalCodeRegistry)
        results = goal_code_registry.goal_codes_matching_query(match)
        return results

    async def receive_query(self, queries_msg: Queries) -> Disclosures:
        """Process query and return the corresponding disclose message."""
        disclosures = Disclosures(disclosures=[])
        published_results = []
        (
            to_publish_protocols,
            to_publish_goal_codes,
        ) = await self.return_to_publish_features()
        for query_item in queries_msg.queries:
            assert isinstance(query_item, QueryItem)
            if query_item.feature_type == "protocol":
                results = await self.execute_protocol_query(query_item.match)
                for result in results:
                    to_publish_result = {"feature-type": "protocol"}
                    if "pid" in result:
                        if (
                            to_publish_protocols
                            and result.get("pid") not in to_publish_protocols
                        ):
                            continue
                        to_publish_result["id"] = result.get("pid")
                    else:
                        continue
                    if "roles" in result:
                        to_publish_result["roles"] = result.get("roles")
                    published_results.append(to_publish_result)
            elif query_item.feature_type == "goal-code":
                results = await self.execute_goal_code_query(query_item.match)
                for result in results:
                    to_publish_result = {"feature-type": "goal-code"}
                    if to_publish_goal_codes and result not in to_publish_goal_codes:
                        continue
                    to_publish_result["id"] = result
                    published_results.append(to_publish_result)
        disclosures.disclosures = published_results
        # Check if query message has a thid
        # If disclosing this agents feature
        if queries_msg._thread:
            disclosures.assign_thread_id(queries_msg._thread.thid)
        return disclosures

    async def check_if_disclosure_received(
        self, record_id: str
    ) -> V20DiscoveryExchangeRecord:
        """Check if disclosures has been received."""
        while True:
            async with self._profile.session() as session:
                ex_rec = await V20DiscoveryExchangeRecord.retrieve_by_id(
                    session=session, record_id=record_id
                )
            if ex_rec.disclosures:
                return ex_rec
            await asyncio.sleep(0.5)

    async def create_and_send_query(
        self,
        connection_id: str = None,
        query_protocol: str = None,
        query_goal_code: str = None,
    ) -> V20DiscoveryExchangeRecord:
        """Create and send a Query message."""
        queries = []
        if not query_goal_code and not query_protocol:
            raise V20DiscoveryMgrError(
                "Atleast one protocol or goal-code feature-type query is required."
            )
        if query_protocol:
            queries.append(QueryItem(feature_type="protocol", match=query_protocol))
        if query_goal_code:
            queries.append(QueryItem(feature_type="goal-code", match=query_goal_code))
        queries_msg = Queries(queries=queries)
        if connection_id:
            async with self._profile.session() as session:
                # If existing record exists for a connection_id
                if await V20DiscoveryExchangeRecord.exists_for_connection_id(
                    session=session, connection_id=connection_id
                ):
                    discovery_ex_rec = (
                        await V20DiscoveryExchangeRecord.retrieve_by_connection_id(
                            session=session, connection_id=connection_id
                        )
                    )
                    discovery_ex_rec.disclosures = None
                    await discovery_ex_rec.save(session)
                else:
                    discovery_ex_rec = V20DiscoveryExchangeRecord()
                discovery_ex_rec.queries_msg = queries_msg
                discovery_ex_rec.connection_id = connection_id
                await discovery_ex_rec.save(session)
            queries_msg.assign_thread_id(discovery_ex_rec.discovery_exchange_id)
            responder = self.profile.inject_or(BaseResponder)
            if responder:
                await responder.send(queries_msg, connection_id=connection_id)
            else:
                self._logger.exception(
                    "Unable to send discover-features v2 query message"
                    ": BaseResponder unavailable"
                )
            try:
                return await asyncio.wait_for(
                    self.check_if_disclosure_received(
                        record_id=discovery_ex_rec.discovery_exchange_id,
                    ),
                    5,
                )
            except asyncio.TimeoutError:
                return discovery_ex_rec
        else:
            # Disclose this agent's features and/or goal codes
            discovery_ex_rec = V20DiscoveryExchangeRecord()
            discovery_ex_rec.queries_msg = queries_msg
            disclosures = await self.receive_query(queries_msg=queries_msg)
            discovery_ex_rec.disclosures = disclosures
            return discovery_ex_rec
