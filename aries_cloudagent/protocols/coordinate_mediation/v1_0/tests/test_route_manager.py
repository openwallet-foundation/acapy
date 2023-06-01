from asynctest import mock
import pytest

from .....connections.models.conn_record import ConnRecord
from .....core.in_memory import InMemoryProfile
from .....wallet.base import BaseWallet
from .....core.profile import Profile
from .....messaging.responder import BaseResponder, MockResponder
from .....storage.error import StorageNotFoundError
from .....wallet.did_info import DIDInfo
from .....wallet.in_memory import InMemoryWallet
from ....routing.v1_0.models.route_record import RouteRecord
from ..manager import MediationManager
from ..messages.keylist_update import KeylistUpdate
from ..models.mediation_record import MediationRecord
from ..route_manager import (
    CoordinateMediationV1RouteManager,
    RouteManager,
    RouteManagerError,
)

TEST_RECORD_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_VERKEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
TEST_ROUTE_RECORD_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
TEST_ROUTE_VERKEY = "did:key:z6MknxTj6Zj1VrDWc1ofaZtmCVv2zNXpD58Xup4ijDGoQhya"


class MockRouteManager(RouteManager):
    """Concretion of RouteManager for testing."""

    _route_for_key = mock.CoroutineMock()
    routing_info = mock.CoroutineMock()


@pytest.fixture
def mock_responder():
    yield MockResponder()


@pytest.fixture
def profile(mock_responder: MockResponder):
    yield InMemoryProfile.test_profile(bind={BaseResponder: mock_responder})


@pytest.fixture
def route_manager():
    manager = MockRouteManager()
    manager._route_for_key = mock.CoroutineMock(
        return_value=mock.MagicMock(KeylistUpdate)
    )
    manager.routing_info = mock.CoroutineMock(return_value=([], "http://example.com"))
    yield manager


@pytest.fixture
def mediation_route_manager():
    yield CoordinateMediationV1RouteManager()


@pytest.fixture
def conn_record():
    record = ConnRecord(connection_id="12345")
    record.metadata_get = mock.CoroutineMock(return_value={})
    record.metadata_set = mock.CoroutineMock()
    yield record


@pytest.mark.asyncio
async def test_get_or_create_my_did_no_did(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    conn_record.my_did = None
    mock_did_info = mock.MagicMock()
    with mock.patch.object(
        InMemoryWallet,
        "create_local_did",
        mock.CoroutineMock(return_value=mock_did_info),
    ) as mock_create_local_did, mock.patch.object(
        conn_record, "save", mock.CoroutineMock()
    ) as mock_save:
        info = await route_manager.get_or_create_my_did(profile, conn_record)
        assert mock_did_info == info
        mock_create_local_did.assert_called_once()
        mock_save.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_my_did_existing_did(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    conn_record.my_did = "test-did"
    mock_did_info = mock.MagicMock(DIDInfo)
    with mock.patch.object(
        InMemoryWallet, "get_local_did", mock.CoroutineMock(return_value=mock_did_info)
    ) as mock_get_local_did:
        info = await route_manager.get_or_create_my_did(profile, conn_record)
        assert mock_did_info == info
        mock_get_local_did.assert_called_once()


@pytest.mark.asyncio
async def test_mediation_record_for_connection_mediation_id(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    with mock.patch.object(
        route_manager,
        "mediation_record_if_id",
        mock.CoroutineMock(return_value=mediation_record),
    ) as mock_mediation_record_if_id, mock.patch.object(
        route_manager, "save_mediator_for_connection", mock.CoroutineMock()
    ):
        assert (
            await route_manager.mediation_record_for_connection(
                profile, conn_record, mediation_record.mediation_id
            )
            == mediation_record
        )
        mock_mediation_record_if_id.assert_called_once_with(
            profile, mediation_record.mediation_id, False
        )


@pytest.mark.asyncio
async def test_mediation_record_for_connection_mediation_metadata(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    conn_record.metadata_get.return_value = {
        MediationManager.METADATA_ID: mediation_record.mediation_id
    }
    with mock.patch.object(
        route_manager,
        "mediation_record_if_id",
        mock.CoroutineMock(return_value=mediation_record),
    ) as mock_mediation_record_if_id, mock.patch.object(
        route_manager, "save_mediator_for_connection", mock.CoroutineMock()
    ):
        assert (
            await route_manager.mediation_record_for_connection(
                profile, conn_record, "another-mediation-id"
            )
            == mediation_record
        )
        mock_mediation_record_if_id.assert_called_once_with(
            profile, mediation_record.mediation_id, False
        )


@pytest.mark.asyncio
async def test_mediation_record_for_connection_default(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    with mock.patch.object(
        route_manager,
        "mediation_record_if_id",
        mock.CoroutineMock(return_value=mediation_record),
    ) as mock_mediation_record_if_id, mock.patch.object(
        route_manager, "save_mediator_for_connection", mock.CoroutineMock()
    ):
        assert (
            await route_manager.mediation_record_for_connection(
                profile, conn_record, None, or_default=True
            )
            == mediation_record
        )
        mock_mediation_record_if_id.assert_called_once_with(profile, None, True)


@pytest.mark.asyncio
async def test_mediation_record_if_id_with_id(
    profile: Profile, route_manager: RouteManager
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id", state=MediationRecord.STATE_GRANTED
    )
    with mock.patch.object(
        MediationRecord,
        "retrieve_by_id",
        mock.CoroutineMock(return_value=mediation_record),
    ) as mock_retrieve_by_id:
        actual = await route_manager.mediation_record_if_id(
            profile, mediation_id=mediation_record.mediation_id
        )
        assert mediation_record == actual
        mock_retrieve_by_id.assert_called_once()


@pytest.mark.asyncio
async def test_mediation_record_if_id_with_id_bad_state(
    profile: Profile, route_manager: RouteManager
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id", state=MediationRecord.STATE_DENIED
    )
    with mock.patch.object(
        MediationRecord,
        "retrieve_by_id",
        mock.CoroutineMock(return_value=mediation_record),
    ):
        with pytest.raises(RouteManagerError):
            await route_manager.mediation_record_if_id(
                profile, mediation_id=mediation_record.mediation_id
            )


@pytest.mark.asyncio
async def test_mediation_record_if_id_with_id_and_default(
    profile: Profile, route_manager: RouteManager
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id", state=MediationRecord.STATE_GRANTED
    )
    with mock.patch.object(
        MediationRecord,
        "retrieve_by_id",
        mock.CoroutineMock(return_value=mediation_record),
    ) as mock_retrieve_by_id, mock.patch.object(
        MediationManager, "get_default_mediator", mock.CoroutineMock()
    ) as mock_get_default_mediator:
        actual = await route_manager.mediation_record_if_id(
            profile, mediation_id=mediation_record.mediation_id, or_default=True
        )
        assert mediation_record == actual
        mock_retrieve_by_id.assert_called_once()
        mock_get_default_mediator.assert_not_called()


@pytest.mark.asyncio
async def test_mediation_record_if_id_without_id_and_default(
    profile: Profile,
    route_manager: RouteManager,
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id", state=MediationRecord.STATE_GRANTED
    )
    with mock.patch.object(
        MediationRecord, "retrieve_by_id", mock.CoroutineMock()
    ) as mock_retrieve_by_id, mock.patch.object(
        MediationManager,
        "get_default_mediator",
        mock.CoroutineMock(return_value=mediation_record),
    ) as mock_get_default_mediator:
        actual = await route_manager.mediation_record_if_id(
            profile, mediation_id=None, or_default=True
        )
        assert mediation_record == actual
        mock_retrieve_by_id.assert_not_called()
        mock_get_default_mediator.assert_called_once()


@pytest.mark.asyncio
async def test_mediation_record_if_id_without_id_and_no_default(
    profile: Profile,
    route_manager: RouteManager,
):
    with mock.patch.object(
        MediationRecord, "retrieve_by_id", mock.CoroutineMock(return_value=None)
    ) as mock_retrieve_by_id, mock.patch.object(
        MediationManager, "get_default_mediator", mock.CoroutineMock(return_value=None)
    ) as mock_get_default_mediator:
        assert (
            await route_manager.mediation_record_if_id(
                profile, mediation_id=None, or_default=True
            )
            is None
        )
        mock_retrieve_by_id.assert_not_called()
        mock_get_default_mediator.assert_called_once()


@pytest.mark.asyncio
async def test_route_connection_as_invitee(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    mock_did_info = mock.MagicMock(DIDInfo)
    with mock.patch.object(
        route_manager,
        "get_or_create_my_did",
        mock.CoroutineMock(return_value=mock_did_info),
    ):
        await route_manager.route_connection_as_invitee(
            profile, conn_record, mediation_record
        )
        route_manager._route_for_key.assert_called_once_with(
            profile, mock_did_info.verkey, mediation_record, skip_if_exists=True
        )


@pytest.mark.asyncio
async def test_route_connection_as_inviter(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    mock_did_info = mock.MagicMock(DIDInfo)
    conn_record.invitation_key = "test-invitation-key"
    with mock.patch.object(
        route_manager,
        "get_or_create_my_did",
        mock.CoroutineMock(return_value=mock_did_info),
    ):
        await route_manager.route_connection_as_inviter(
            profile, conn_record, mediation_record
        )
        route_manager._route_for_key.assert_called_once_with(
            profile,
            mock_did_info.verkey,
            mediation_record,
            replace_key="test-invitation-key",
            skip_if_exists=True,
        )


@pytest.mark.asyncio
async def test_route_connection_state_invitee(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    conn_record.state = "invitation"
    conn_record.their_role = "responder"
    with mock.patch.object(
        route_manager, "route_connection_as_invitee", mock.CoroutineMock()
    ) as mock_route_connection_as_invitee, mock.patch.object(
        route_manager, "route_connection_as_inviter", mock.CoroutineMock()
    ) as mock_route_connection_as_inviter:
        await route_manager.route_connection(profile, conn_record, mediation_record)
        mock_route_connection_as_invitee.assert_called_once()
        mock_route_connection_as_inviter.assert_not_called()


@pytest.mark.asyncio
async def test_route_connection_state_inviter(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    conn_record.state = "request"
    conn_record.their_role = "requester"
    with mock.patch.object(
        route_manager, "route_connection_as_invitee", mock.CoroutineMock()
    ) as mock_route_connection_as_invitee, mock.patch.object(
        route_manager, "route_connection_as_inviter", mock.CoroutineMock()
    ) as mock_route_connection_as_inviter:
        await route_manager.route_connection(profile, conn_record, mediation_record)
        mock_route_connection_as_inviter.assert_called_once()
        mock_route_connection_as_invitee.assert_not_called()


@pytest.mark.asyncio
async def test_route_connection_state_other(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    conn_record.state = "response"
    conn_record.their_role = "requester"
    assert (
        await route_manager.route_connection(profile, conn_record, mediation_record)
        is None
    )


@pytest.mark.asyncio
async def test_route_invitation_with_key(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    conn_record.invitation_key = "test-invitation-key"
    with mock.patch.object(
        route_manager, "save_mediator_for_connection", mock.CoroutineMock()
    ):
        await route_manager.route_invitation(profile, conn_record, mediation_record)
        route_manager._route_for_key.assert_called_once()


@pytest.mark.asyncio
async def test_route_invitation_without_key(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    with mock.patch.object(
        route_manager, "save_mediator_for_connection", mock.CoroutineMock()
    ):
        with pytest.raises(ValueError):
            await route_manager.route_invitation(profile, conn_record, mediation_record)
        route_manager._route_for_key.assert_not_called()


@pytest.mark.asyncio
async def test_route_public_did(profile: Profile, route_manager: RouteManager):
    await route_manager.route_public_did(profile, "test-verkey")
    route_manager._route_for_key.assert_called_once_with(
        profile, "test-verkey", skip_if_exists=True
    )


@pytest.mark.asyncio
async def test_route_verkey(profile: Profile, route_manager: RouteManager):
    await route_manager.route_verkey(profile, "test-verkey")
    route_manager._route_for_key.assert_called_once_with(
        profile, "test-verkey", skip_if_exists=True
    )


@pytest.mark.asyncio
async def test_route_static(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    mock_did_info = mock.MagicMock(DIDInfo)
    conn_record.invitation_key = "test-invitation-key"
    with mock.patch.object(
        route_manager,
        "get_or_create_my_did",
        mock.CoroutineMock(return_value=mock_did_info),
    ):
        await route_manager.route_static(profile, conn_record, mediation_record)
        route_manager._route_for_key.assert_called_once_with(
            profile,
            mock_did_info.verkey,
            mediation_record,
            skip_if_exists=True,
        )


@pytest.mark.asyncio
async def test_save_mediator_for_connection_record(
    profile: Profile,
    route_manager: RouteManager,
    conn_record: ConnRecord,
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    session = mock.MagicMock()
    profile.session = mock.MagicMock(return_value=session)
    session.__aenter__ = mock.CoroutineMock(return_value=session)
    session.__aexit__ = mock.CoroutineMock()
    with mock.patch.object(
        MediationRecord, "retrieve_by_id", mock.CoroutineMock()
    ) as mock_retrieve_by_id:
        await route_manager.save_mediator_for_connection(
            profile, conn_record, mediation_record
        )
        mock_retrieve_by_id.assert_not_called()
        conn_record.metadata_set.assert_called_once_with(
            session,
            MediationManager.METADATA_KEY,
            {MediationManager.METADATA_ID: mediation_record.mediation_id},
        )


@pytest.mark.asyncio
async def test_save_mediator_for_connection_id(
    profile: Profile,
    route_manager: RouteManager,
    conn_record: ConnRecord,
):
    mediation_record = MediationRecord(mediation_id="test-mediation-id")
    session = mock.MagicMock()
    profile.session = mock.MagicMock(return_value=session)
    session.__aenter__ = mock.CoroutineMock(return_value=session)
    session.__aexit__ = mock.CoroutineMock()
    with mock.patch.object(
        MediationRecord,
        "retrieve_by_id",
        mock.CoroutineMock(return_value=mediation_record),
    ) as mock_retrieve_by_id:
        await route_manager.save_mediator_for_connection(
            profile, conn_record, mediation_id=mediation_record.mediation_id
        )
        mock_retrieve_by_id.assert_called_once()
        conn_record.metadata_set.assert_called_once_with(
            session,
            MediationManager.METADATA_KEY,
            {MediationManager.METADATA_ID: mediation_record.mediation_id},
        )


@pytest.mark.asyncio
async def test_save_mediator_for_connection_no_mediator(
    profile: Profile,
    route_manager: RouteManager,
    conn_record: ConnRecord,
):
    with mock.patch.object(
        MediationRecord, "retrieve_by_id", mock.CoroutineMock()
    ) as mock_retrieve_by_id:
        await route_manager.save_mediator_for_connection(profile, conn_record)
        mock_retrieve_by_id.assert_not_called()
        conn_record.metadata_set.assert_not_called()


@pytest.mark.asyncio
async def test_connection_from_recipient_key_invite(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    with mock.patch.object(
        ConnRecord,
        "retrieve_by_tag_filter",
        mock.CoroutineMock(return_value=conn_record),
    ):
        result = await route_manager.connection_from_recipient_key(profile, TEST_VERKEY)
        assert conn_record == result


@pytest.mark.asyncio
async def test_connection_from_recipient_key_local_did(
    profile: Profile, route_manager: RouteManager, conn_record: ConnRecord
):
    mock_provider = mock.MagicMock()
    mock_wallet = mock.MagicMock()
    mock_wallet.get_local_did_for_verkey = mock.CoroutineMock()
    mock_provider.provide = mock.MagicMock(return_value=mock_wallet)
    session = await profile.session()
    session.context.injector.bind_provider(BaseWallet, mock_provider)
    with mock.patch.object(
        profile, "session", mock.MagicMock(return_value=session)
    ), mock.patch.object(
        ConnRecord, "retrieve_by_did", mock.CoroutineMock(return_value=conn_record)
    ):
        result = await route_manager.connection_from_recipient_key(profile, TEST_VERKEY)
        assert conn_record == result


@pytest.mark.asyncio
async def test_mediation_route_for_key(
    profile: Profile,
    mediation_route_manager: CoordinateMediationV1RouteManager,
    mock_responder: MockResponder,
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id", connection_id="test-mediator-conn-id"
    )
    keylist_update = await mediation_route_manager._route_for_key(
        profile,
        TEST_VERKEY,
        mediation_record,
        skip_if_exists=False,
        replace_key=None,
    )
    assert keylist_update
    assert keylist_update.serialize()["updates"] == [
        {"action": "add", "recipient_key": TEST_VERKEY}
    ]
    assert mock_responder.messages
    assert (
        keylist_update,
        {"connection_id": "test-mediator-conn-id"},
    ) == mock_responder.messages[0]


@pytest.mark.asyncio
async def test_mediation_route_for_key_skip_if_exists_and_exists(
    profile: Profile,
    mediation_route_manager: CoordinateMediationV1RouteManager,
    mock_responder: MockResponder,
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id", connection_id="test-mediator-conn-id"
    )
    with mock.patch.object(
        RouteRecord, "retrieve_by_recipient_key", mock.CoroutineMock()
    ):
        keylist_update = await mediation_route_manager._route_for_key(
            profile,
            TEST_VERKEY,
            mediation_record,
            skip_if_exists=True,
            replace_key=None,
        )
    assert keylist_update is None
    assert not mock_responder.messages


@pytest.mark.asyncio
async def test_mediation_route_for_key_skip_if_exists_and_absent(
    profile: Profile,
    mediation_route_manager: CoordinateMediationV1RouteManager,
    mock_responder: MockResponder,
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id", connection_id="test-mediator-conn-id"
    )
    with mock.patch.object(
        RouteRecord,
        "retrieve_by_recipient_key",
        mock.CoroutineMock(side_effect=StorageNotFoundError),
    ):
        keylist_update = await mediation_route_manager._route_for_key(
            profile,
            TEST_VERKEY,
            mediation_record,
            skip_if_exists=True,
            replace_key=None,
        )
    assert keylist_update
    assert keylist_update.serialize()["updates"] == [
        {"action": "add", "recipient_key": TEST_VERKEY}
    ]
    assert mock_responder.messages
    assert (
        keylist_update,
        {"connection_id": "test-mediator-conn-id"},
    ) == mock_responder.messages[0]


@pytest.mark.asyncio
async def test_mediation_route_for_key_replace_key(
    profile: Profile,
    mediation_route_manager: CoordinateMediationV1RouteManager,
    mock_responder: MockResponder,
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id", connection_id="test-mediator-conn-id"
    )
    keylist_update = await mediation_route_manager._route_for_key(
        profile,
        TEST_VERKEY,
        mediation_record,
        skip_if_exists=False,
        replace_key=TEST_ROUTE_VERKEY,
    )
    assert keylist_update
    assert keylist_update.serialize()["updates"] == [
        {"action": "add", "recipient_key": TEST_VERKEY},
        {"action": "remove", "recipient_key": TEST_ROUTE_VERKEY},
    ]
    assert mock_responder.messages
    assert (
        keylist_update,
        {"connection_id": "test-mediator-conn-id"},
    ) == mock_responder.messages[0]


@pytest.mark.asyncio
async def test_mediation_route_for_key_no_mediator(
    profile: Profile,
    mediation_route_manager: CoordinateMediationV1RouteManager,
):
    assert (
        await mediation_route_manager._route_for_key(
            profile,
            TEST_VERKEY,
            None,
            skip_if_exists=True,
            replace_key=TEST_ROUTE_VERKEY,
        )
        is None
    )


@pytest.mark.asyncio
async def test_mediation_routing_info_with_mediator(
    profile: Profile,
    mediation_route_manager: CoordinateMediationV1RouteManager,
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id",
        connection_id="test-mediator-conn-id",
        routing_keys=["test-key-0", "test-key-1"],
        endpoint="http://mediator.example.com",
    )
    keys, endpoint = await mediation_route_manager.routing_info(
        profile, "http://example.com", mediation_record
    )
    assert keys == mediation_record.routing_keys
    assert endpoint == mediation_record.endpoint


@pytest.mark.asyncio
async def test_mediation_routing_info_no_mediator(
    profile: Profile,
    mediation_route_manager: CoordinateMediationV1RouteManager,
):
    keys, endpoint = await mediation_route_manager.routing_info(
        profile, "http://example.com", None
    )
    assert keys == []
    assert endpoint == "http://example.com"
