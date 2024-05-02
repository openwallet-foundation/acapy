"""Test mediation record."""

import json

import pytest

from ......core.in_memory import InMemoryProfile
from ......core.profile import ProfileSession
from ......storage.base import BaseStorage
from ......storage.record import StorageRecord
from ..mediation_record import MediationRecord


@pytest.fixture()
async def session():
    profile = InMemoryProfile.test_profile()
    async with profile.session() as session:
        yield session


@pytest.mark.asyncio
async def test_backwards_compat_terms(session: ProfileSession):
    """Make sure old records can be loaded still."""

    old_record = StorageRecord(
        MediationRecord.RECORD_TYPE,
        id="test_mediation_id",
        value=json.dumps(
            {
                "state": "granted",
                "mediator_terms": ["dummy_terms"],
                "recipient_terms": ["dummy_terms"],
            }
        ),
    )
    storage = session.inject(BaseStorage)
    await storage.add_record(old_record)

    record = await MediationRecord.retrieve_by_id(session, old_record.id)
    assert isinstance(record, MediationRecord)
    assert record.mediation_id == "test_mediation_id"
    assert record.state == "granted"


@pytest.mark.asyncio
async def test_mediation_record_eq():
    record_0 = MediationRecord(mediation_id="test_medation_id_0", endpoint="zero")
    record_1 = MediationRecord(mediation_id="test_medation_id_1", endpoint="one")
    assert record_0 != record_1

    with pytest.raises(ValueError):
        record_0.state = "bad state"


@pytest.mark.asyncio
async def test_mediation_record_duplicate_means_exists(session: ProfileSession):
    await MediationRecord(connection_id="test_connection_id", endpoint="abc").save(
        session
    )
    await MediationRecord(connection_id="test_connection_id", endpoint="def").save(
        session
    )
    assert await MediationRecord.exists_for_connection_id(session, "test_connection_id")
