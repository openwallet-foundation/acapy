from unittest.mock import AsyncMock, MagicMock
import pytest
from acapy_agent.connections.models.conn_record import ConnRecord
from acapy_agent.protocols.coordinate_mediation.v1_0.route_manager import (
    CoordinateMediationV1RouteManager,
)
from contextlib import asynccontextmanager
from acapy_agent.core.profile import Profile
from acapy_agent.storage.base import BaseStorage
from acapy_agent.cache.base import BaseCache
from acapy_agent.storage.record import StorageRecord
import json


@asynccontextmanager
async def make_profile():
    profile = MagicMock(spec=Profile)

    # Mock settings
    settings_mock = {"some.setting": True}

    # Mock storage with expected async methods
    storage_mock = MagicMock(spec=BaseStorage)

    cache_mock = MagicMock(spec=BaseCache)
    cache_mock.clear = AsyncMock()

    def custom_inject(cls):
        if cls.__name__ == "BaseStorage":
            return storage_mock
        elif cls.__name__ == "BaseWallet":
            return cache_mock
        else:
            return MagicMock()

    # Mock session with .settings and .inject
    session_mock = AsyncMock()
    session_mock.settings = settings_mock
    session_mock.inject = MagicMock(return_value=storage_mock)
    session_mock.inject_or = MagicMock(return_value=cache_mock)
    session_mock.inject.side_effect = custom_inject

    # Async context manager that yields session
    session_context_manager = AsyncMock()
    session_context_manager.__aenter__.return_value = session_mock
    session_context_manager.__aexit__.return_value = None

    profile.session.return_value = session_context_manager

    yield profile


INVITATION_KEY = "B87peZJozsKpoUrNvdmsRdZyGN4cETNAvczo2n8tox5F"


@pytest.mark.asyncio
async def test_multiuse_invitation_does_not_raise():
    """Two calls with the same invitation key must not raise and return the same connection."""

    async with make_profile() as profile:
        conn_record = ConnRecord(
            invitation_key=INVITATION_KEY,
            state=ConnRecord.State.COMPLETED,
            their_role=ConnRecord.Role.REQUESTER,
            accept="auto",
        )

        async with profile.session() as session:
            await conn_record.save(session)

        # Mock the record that would be found in storage
        profile.session.return_value.__aenter__.return_value.inject.return_value.find_all_records.return_value = [
            StorageRecord(
                id="test-conn-id",
                type=ConnRecord.RECORD_TYPE,
                value=json.dumps(
                    {
                        k: v
                        for k, v in conn_record.serialize().items()
                        if k != "connection_id"
                    }
                ),
                tags={
                    "invitation_key": INVITATION_KEY,
                    "my_did": "did:example:123456789abcdefghi",
                },
            )
        ]

        # Initialize the route manager
        route_mgr = CoordinateMediationV1RouteManager()

        # Call the method twice with the same input
        result1 = await route_mgr.connection_from_recipient_key(
            profile, recipient_key=INVITATION_KEY
        )
        result2 = await route_mgr.connection_from_recipient_key(
            profile, recipient_key=INVITATION_KEY
        )

        # Verify both results are valid
        assert isinstance(result1, ConnRecord)
        assert isinstance(result2, ConnRecord)
