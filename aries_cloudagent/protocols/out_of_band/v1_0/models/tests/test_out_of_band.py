import pytest

from ..oob_record import OobRecord
from ...messages.invitation import InvitationMessage
from ......core.in_memory import InMemoryProfile
from ......core.profile import ProfileSession


@pytest.fixture()
async def session():
    profile = InMemoryProfile.test_profile()
    async with profile.session() as session:
        yield session


@pytest.mark.asyncio
async def test_oob_record_multi_use(session: ProfileSession):
    """Test oob record multi_use."""
    invi_msg = InvitationMessage(handshake_protocols=["connections/1.0"])
    oob_rec = OobRecord(
        state=OobRecord.STATE_INITIAL,
        invi_msg_id="67890",
        role=OobRecord.ROLE_SENDER,
        invitation=invi_msg,
        multi_use=True,
    )

    await oob_rec.save(session)
    saved_record = await OobRecord.retrieve_by_id(session, record_id=oob_rec.oob_id)
    assert saved_record
    assert isinstance(saved_record, OobRecord)
    assert oob_rec.multi_use
    assert saved_record.multi_use
