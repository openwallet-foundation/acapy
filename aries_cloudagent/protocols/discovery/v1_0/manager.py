"""Classes to manage discover features."""

import asyncio
import logging

from typing import Optional

from ....core.error import BaseError
from ....core.profile import Profile
from ....core.protocol_registry import ProtocolRegistry
from ....storage.error import StorageNotFoundError
from ....messaging.responder import BaseResponder

from .messages.disclose import Disclose
from .messages.query import Query
from .models.discovery_record import V10DiscoveryExchangeRecord as DiscRecord


class V10DiscoveryMgrError(BaseError):
    """Discover feature v1_0 error."""


class V10DiscoveryMgr:
    """Class for discover feature v1_0 under RFC 31."""

    def __init__(self, profile: Profile):
        """Initialize a V10DiscoveryMgr.

        Args:
            profile: The profile for this manager
        """
        self._profile = profile
        self._logger = logging.getLogger(__name__)

    @property
    def profile(self) -> Profile:
        """Accessor for the current Profile.

        Returns:
            The Profile for this manager

        """
        return self._profile

    async def receive_disclose(
        self, disclose_msg: Disclose, connection_id: str
    ) -> DiscRecord:
        """Receive Disclose message and return updated V10DiscoveryExchangeRecord."""
        async with self._profile.session() as session:
            record = None
            if disclose_msg._thread:
                thread_id = disclose_msg._thread.thid
                try:
                    record = await DiscRecord.retrieve_by_id(
                        session=session, record_id=thread_id
                    )
                except StorageNotFoundError:
                    pass

            if not record:
                record = await DiscRecord.retrieve_if_exists_by_connection_id(
                    session, connection_id
                )

            if not record:
                record = DiscRecord()

            record.connection_id = connection_id
            record.disclose = disclose_msg
            record.state = DiscRecord.STATE_DISCLOSE_RECV
            await record.save(session)

        return record

    async def lookup_exchange_rec_by_connection(
        self, connection_id: str
    ) -> Optional[DiscRecord]:
        """Retrieve V20DiscoveryExchangeRecord by connection_id."""
        async with self._profile.session() as session:
            if await DiscRecord.exists_for_connection_id(
                session=session, connection_id=connection_id
            ):
                return await DiscRecord.retrieve_by_connection_id(
                    session=session, connection_id=connection_id
                )
            else:
                return None

    async def receive_query(self, query_msg: Query) -> Disclose:
        """Process query and return the corresponding disclose message."""
        registry = self._profile.context.inject(ProtocolRegistry)
        query_str = query_msg.query
        published_results = []
        protocols = registry.protocols_matching_query(query_str)
        results = await registry.prepare_disclosed(self._profile.context, protocols)

        async with self._profile.session() as session:
            to_publish_protocols = None
            if (
                session.settings.get("disclose_protocol_list")
                and len(session.settings.get("disclose_protocol_list")) > 0
            ):
                to_publish_protocols = session.settings.get("disclose_protocol_list")

            for result in results:
                to_publish_result = {}
                if "pid" in result:
                    if (
                        to_publish_protocols
                        and result.get("pid") not in to_publish_protocols
                    ):
                        continue

                    to_publish_result["pid"] = result.get("pid")
                else:
                    continue

                if "roles" in result:
                    to_publish_result["roles"] = result.get("roles")

                published_results.append(to_publish_result)

        disclose_msg = Disclose(protocols=published_results)
        # Check if query message has a thid
        # If disclosing this agents feature
        if query_msg._thread:
            disclose_msg.assign_thread_id(query_msg._thread.thid)
        return disclose_msg

    async def check_if_disclosure_received(self, record_id: str) -> DiscRecord:
        """Check if disclosures has been received."""
        while True:
            async with self._profile.session() as session:
                ex_rec = await DiscRecord.retrieve_by_id(
                    session=session, record_id=record_id
                )
            if ex_rec.disclose:
                return ex_rec
            await asyncio.sleep(0.5)

    async def create_and_send_query(
        self,
        query: str,
        comment: Optional[str] = None,
        connection_id: Optional[str] = None,
    ) -> DiscRecord:
        """Create and send a Query message."""
        query_msg = Query(query=query, comment=comment)
        if not connection_id:
            # Disclose this agent's features and/or goal codes
            record = DiscRecord()
            record.query_msg = query_msg
            disclose = await self.receive_query(query_msg=query_msg)
            record.disclose = disclose
            return record

        record = None
        async with self._profile.session() as session:
            record = await DiscRecord.retrieve_if_exists_by_connection_id(
                session=session, connection_id=connection_id
            )

            if record:
                record.disclose = None
            else:
                record = DiscRecord()

        record.state = DiscRecord.STATE_QUERY_SENT
        record.query_msg = query_msg
        record.connection_id = connection_id

        query_msg.assign_thread_id(record.discovery_exchange_id)
        responder = self._profile.inject(BaseResponder)

        await responder.send(query_msg, connection_id=connection_id)

        async with self._profile.session() as session:
            await record.save(session)

        try:
            return await asyncio.wait_for(
                self.check_if_disclosure_received(
                    record_id=record.discovery_exchange_id,
                ),
                5,
            )

        except asyncio.TimeoutError:
            return record
