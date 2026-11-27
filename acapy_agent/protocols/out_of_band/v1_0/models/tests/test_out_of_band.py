import pytest
import pytest_asyncio

from ......connections.models.conn_record import ConnRecord
from ......core.profile import ProfileSession
from ......utils.testing import create_test_profile
from ...messages.invitation import InvitationMessage
from ..oob_record import OobRecord


@pytest_asyncio.fixture
async def session():
    profile = await create_test_profile()
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


@pytest.mark.asyncio
async def test_oob_delete_preserves_connection_metadata(session: ProfileSession):
    """Deleting a finished OOB record must not wipe ConnRecord metadata."""
    conn = ConnRecord(
        invitation_key="3Dn1SJNPaCXcvvJvSbsFWP2xaCjMagAhtJrApWoKJ9XM",
        their_label="Peer",
        state=ConnRecord.State.INVITATION.rfc23,
        invitation_mode="once",
    )
    await conn.save(session)
    await conn.metadata_set(session, "purpose", {"flow": "issue"})

    invi_msg = InvitationMessage(handshake_protocols=["connections/1.0"])
    oob_rec = OobRecord(
        state=OobRecord.STATE_DONE,
        invi_msg_id="invi-msg-1",
        role=OobRecord.ROLE_SENDER,
        invitation=invi_msg,
        connection_id=conn.connection_id,
        multi_use=False,
    )
    await oob_rec.save(session)
    await oob_rec.delete_record(session)

    assert await conn.metadata_get(session, "purpose") == {"flow": "issue"}
    assert await conn.metadata_get_all(session) == {"purpose": {"flow": "issue"}}
