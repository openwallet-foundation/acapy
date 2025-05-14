# acapy_agent/protocols/coordinate_mediation/v1_0/tests/test_multiuse_invitation.py
from unittest.mock import AsyncMock, MagicMock
from acapy_agent.connections.models.diddoc.publickey import PublicKeyType
import pytest

# ✅  local package – NOT aries_cloudagent.*
from acapy_agent.connections.models.conn_record import ConnRecord
from acapy_agent.protocols.coordinate_mediation.v1_0.route_manager import (
    CoordinateMediationV1RouteManager,
)
from contextlib import asynccontextmanager
from acapy_agent.core.profile import Profile
from acapy_agent.storage.base import BaseStorage
from acapy_agent.cache.base import BaseCache
from acapy_agent.multitenant.base import BaseMultitenantManager
from acapy_agent.wallet.base import BaseWallet
from acapy_agent.wallet.did_info import DIDInfo
from acapy_agent.storage.record import StorageRecord
import json


@asynccontextmanager
async def make_profile():
    profile = MagicMock(spec=Profile)

    # Mock settings
    settings_mock = {"some.setting": True}

    # Mock storage with expected async methods
    storage_mock = MagicMock(spec=BaseStorage)
    storage_mock.add_record = AsyncMock()
    storage_mock.update_record = AsyncMock()
    storage_mock.delete_record = AsyncMock()
    storage_mock.get_record = AsyncMock()
    storage_mock.find_record = AsyncMock()
    storage_mock.find_all_records = AsyncMock()

    cache_mock = MagicMock(spec=BaseCache)
    cache_mock.clear = AsyncMock()

    multitenant_manager_mock = AsyncMock(spec=BaseMultitenantManager)
    multitenant_manager_mock.get_profile_for_key.return_value = None  # Simulate fallback

    wallet_mock = AsyncMock(spec=BaseWallet)
    wallet_mock.get_local_did_for_verkey.return_value = DIDInfo(
        did="did:example:123456789abcdefghi",
        verkey=INVITATION_KEY,
        metadata={},
        method="sov",
        key_type=PublicKeyType.ED25519_SIG_2018,  # ← this is the required missing argument
    )

    # Mock session with .settings and .inject
    session_mock = AsyncMock()
    session_mock.settings = settings_mock
    session_mock.inject = MagicMock(return_value=storage_mock)
    session_mock.inject_or = MagicMock(return_value=cache_mock)
    session_mock.inject.side_effect = lambda cls: (
        storage_mock
        if cls.__name__ == "BaseStorage"
        else cache_mock
        if cls.__name__ == "BaseCache"
        else multitenant_manager_mock
        if cls.__name__ == "BaseMultitenantManager"
        else wallet_mock
        if cls.__name__ == "BaseWallet"
        else MagicMock()
    )

    # Async context manager that yields session
    session_context_manager = AsyncMock()
    session_context_manager.__aenter__.return_value = session_mock
    session_context_manager.__aexit__.return_value = None

    # profile.session() returns the async context manager
    profile.session.return_value = session_context_manager

    yield profile


INVITATION_KEY = "B87peZJozsKpoUrNvdmsRdZyGN4cETNAvczo2n8tox5F"


@pytest.mark.asyncio
async def test_multiuse_invitation_does_not_raise():
    """Two connections that share an invitation key must not raise."""
    async with make_profile() as profile:
        for _ in range(2):
            conn_record = ConnRecord(
                invitation_key=INVITATION_KEY,
                state=ConnRecord.State.COMPLETED,
                their_role=ConnRecord.Role.REQUESTER,
                accept="auto",
            )
            async with profile.session() as session:
                await conn_record.save(session)

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

        route_mgr = CoordinateMediationV1RouteManager()

        # call the classmethod twice
        # Call the method twice and store both results
        result1 = await route_mgr.connection_from_recipient_key(
            profile, recipient_key=INVITATION_KEY
        )
        result2 = await route_mgr.connection_from_recipient_key(
            profile, recipient_key=INVITATION_KEY
        )

        # Assert both are ConnRecords
        assert isinstance(result1, ConnRecord)
        assert isinstance(result2, ConnRecord)

        # Assert they are the same connection (same ID)
        assert result1.connection_id == result2.connection_id
