from asynctest import mock
import pytest

from ...core.in_memory import InMemoryProfile
from ...core.profile import Profile
from ...messaging.responder import BaseResponder, MockResponder
from ...messaging.responder import BaseResponder, MockResponder
from ...protocols.coordinate_mediation.v1_0.models.mediation_record import (
    MediationRecord,
)
from ...protocols.routing.v1_0.manager import RoutingManager
from ...protocols.routing.v1_0.models.route_record import RouteRecord
from ...storage.error import StorageNotFoundError
from ..route_manager import MultitenantRouteManager


@pytest.fixture
def wallet_id():
    yield "test-wallet-id"


@pytest.fixture
def mock_responder():
    yield MockResponder()


@pytest.fixture
def root_profile(mock_responder: MockResponder):
    yield InMemoryProfile.test_profile(
        bind={
            BaseResponder: mock_responder,
        }
    )


@pytest.fixture
def sub_profile(mock_responder: MockResponder, wallet_id: str):
    yield InMemoryProfile.test_profile(
        settings={
            "wallet.id": wallet_id,
        },
        bind={
            BaseResponder: mock_responder,
        },
    )


@pytest.fixture
def route_manager(root_profile: Profile, sub_profile: Profile, wallet_id: str):
    yield MultitenantRouteManager(root_profile)


@pytest.mark.asyncio
async def test_route_for_key_sub_mediator_no_base_mediator(
    route_manager: MultitenantRouteManager,
    mock_responder: MockResponder,
    wallet_id: str,
    sub_profile: Profile,
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id", connection_id="test-mediator-conn-id"
    )

    with mock.patch.object(
        route_manager, "get_base_wallet_mediator", mock.CoroutineMock(return_value=None)
    ), mock.patch.object(
        RoutingManager, "create_route_record", mock.CoroutineMock()
    ) as mock_create_route_record:
        keylist_update = await route_manager._route_for_key(
            sub_profile,
            "test-recipient-key",
            mediation_record,
            skip_if_exists=False,
            replace_key=None,
        )

    mock_create_route_record.assert_called_once_with(
        recipient_key="test-recipient-key", internal_wallet_id=wallet_id
    )
    assert keylist_update
    assert keylist_update.serialize()["updates"] == [
        {"action": "add", "recipient_key": "test-recipient-key"}
    ]
    assert mock_responder.messages
    assert (
        keylist_update,
        {"connection_id": "test-mediator-conn-id"},
    ) == mock_responder.messages[0]


@pytest.mark.asyncio
async def test_route_for_key_sub_mediator_and_base_mediator(
    sub_profile: Profile,
    route_manager: MultitenantRouteManager,
    mock_responder: MockResponder,
    wallet_id: str,
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id", connection_id="test-mediator-conn-id"
    )
    base_mediation_record = MediationRecord(
        mediation_id="test-base-mediation-id",
        connection_id="test-base-mediator-conn-id",
    )

    with mock.patch.object(
        route_manager,
        "get_base_wallet_mediator",
        mock.CoroutineMock(return_value=base_mediation_record),
    ), mock.patch.object(
        RoutingManager, "create_route_record", mock.CoroutineMock()
    ) as mock_create_route_record:
        keylist_update = await route_manager._route_for_key(
            sub_profile,
            "test-recipient-key",
            mediation_record,
            skip_if_exists=False,
            replace_key=None,
        )

    mock_create_route_record.assert_called_once_with(
        recipient_key="test-recipient-key", internal_wallet_id=wallet_id
    )
    assert keylist_update
    assert keylist_update.serialize()["updates"] == [
        {"action": "add", "recipient_key": "test-recipient-key"}
    ]
    assert mock_responder.messages
    assert (
        keylist_update,
        {"connection_id": "test-base-mediator-conn-id"},
    ) == mock_responder.messages[0]


@pytest.mark.asyncio
async def test_route_for_key_base_mediator_no_sub_mediator(
    sub_profile: Profile,
    route_manager: MultitenantRouteManager,
    mock_responder: MockResponder,
    wallet_id: str,
):
    base_mediation_record = MediationRecord(
        mediation_id="test-base-mediation-id",
        connection_id="test-base-mediator-conn-id",
    )

    with mock.patch.object(
        route_manager,
        "get_base_wallet_mediator",
        mock.CoroutineMock(return_value=base_mediation_record),
    ), mock.patch.object(
        RoutingManager, "create_route_record", mock.CoroutineMock()
    ) as mock_create_route_record:
        keylist_update = await route_manager._route_for_key(
            sub_profile,
            "test-recipient-key",
            None,
            skip_if_exists=False,
            replace_key=None,
        )

    mock_create_route_record.assert_called_once_with(
        recipient_key="test-recipient-key", internal_wallet_id=wallet_id
    )
    assert keylist_update
    assert keylist_update.serialize()["updates"] == [
        {"action": "add", "recipient_key": "test-recipient-key"}
    ]
    assert mock_responder.messages
    assert (
        keylist_update,
        {"connection_id": "test-base-mediator-conn-id"},
    ) == mock_responder.messages[0]


@pytest.mark.asyncio
async def test_route_for_key_skip_if_exists_and_exists(
    sub_profile: Profile,
    route_manager: MultitenantRouteManager,
    mock_responder: MockResponder,
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id", connection_id="test-mediator-conn-id"
    )
    with mock.patch.object(
        RouteRecord, "retrieve_by_recipient_key", mock.CoroutineMock()
    ):
        keylist_update = await route_manager._route_for_key(
            sub_profile,
            "test-recipient-key",
            mediation_record,
            skip_if_exists=True,
            replace_key=None,
        )
    assert keylist_update is None
    assert not mock_responder.messages


@pytest.mark.asyncio
async def test_route_for_key_skip_if_exists_and_absent(
    sub_profile: Profile,
    route_manager: MultitenantRouteManager,
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
        keylist_update = await route_manager._route_for_key(
            sub_profile,
            "test-recipient-key",
            mediation_record,
            skip_if_exists=True,
            replace_key=None,
        )
    assert keylist_update
    assert keylist_update.serialize()["updates"] == [
        {"action": "add", "recipient_key": "test-recipient-key"}
    ]
    assert mock_responder.messages
    assert (
        keylist_update,
        {"connection_id": "test-mediator-conn-id"},
    ) == mock_responder.messages[0]


@pytest.mark.asyncio
async def test_route_for_key_replace_key(
    sub_profile: Profile,
    route_manager: MultitenantRouteManager,
    mock_responder: MockResponder,
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id", connection_id="test-mediator-conn-id"
    )
    keylist_update = await route_manager._route_for_key(
        sub_profile,
        "test-recipient-key",
        mediation_record,
        skip_if_exists=False,
        replace_key="test-replace-key",
    )
    assert keylist_update
    assert keylist_update.serialize()["updates"] == [
        {"action": "add", "recipient_key": "test-recipient-key"},
        {"action": "remove", "recipient_key": "test-replace-key"},
    ]
    assert mock_responder.messages
    assert (
        keylist_update,
        {"connection_id": "test-mediator-conn-id"},
    ) == mock_responder.messages[0]


@pytest.mark.asyncio
async def test_route_for_key_no_mediator(
    sub_profile: Profile,
    route_manager: MultitenantRouteManager,
):
    assert (
        await route_manager._route_for_key(
            sub_profile,
            "test-recipient-key",
            None,
            skip_if_exists=True,
            replace_key="test-replace-key",
        )
        is None
    )


@pytest.mark.asyncio
async def test_routing_info_with_mediator(
    sub_profile: Profile,
    route_manager: MultitenantRouteManager,
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id",
        connection_id="test-mediator-conn-id",
        routing_keys=["test-key-0", "test-key-1"],
        endpoint="http://mediator.example.com",
    )
    keys, endpoint = await route_manager.routing_info(
        sub_profile, "http://example.com", mediation_record
    )
    assert keys == mediation_record.routing_keys
    assert endpoint == mediation_record.endpoint


@pytest.mark.asyncio
async def test_routing_info_no_mediator(
    sub_profile: Profile,
    route_manager: MultitenantRouteManager,
):
    keys, endpoint = await route_manager.routing_info(
        sub_profile, "http://example.com", None
    )
    assert keys == []
    assert endpoint == "http://example.com"


@pytest.mark.asyncio
async def test_routing_info_with_base_mediator(
    sub_profile: Profile,
    route_manager: MultitenantRouteManager,
):
    base_mediation_record = MediationRecord(
        mediation_id="test-base-mediation-id",
        connection_id="test-base-mediator-conn-id",
        routing_keys=["test-key-0", "test-key-1"],
        endpoint="http://base.mediator.example.com",
    )

    with mock.patch.object(
        route_manager,
        "get_base_wallet_mediator",
        mock.CoroutineMock(return_value=base_mediation_record),
    ):
        keys, endpoint = await route_manager.routing_info(
            sub_profile, "http://example.com", None
        )
    assert keys == base_mediation_record.routing_keys
    assert endpoint == base_mediation_record.endpoint


@pytest.mark.asyncio
async def test_routing_info_with_base_mediator_and_sub_mediator(
    sub_profile: Profile,
    route_manager: MultitenantRouteManager,
):
    mediation_record = MediationRecord(
        mediation_id="test-mediation-id",
        connection_id="test-mediator-conn-id",
        routing_keys=["test-key-0", "test-key-1"],
        endpoint="http://mediator.example.com",
    )
    base_mediation_record = MediationRecord(
        mediation_id="test-base-mediation-id",
        connection_id="test-base-mediator-conn-id",
        routing_keys=["test-base-key-0", "test-base-key-1"],
        endpoint="http://base.mediator.example.com",
    )

    with mock.patch.object(
        route_manager,
        "get_base_wallet_mediator",
        mock.CoroutineMock(return_value=base_mediation_record),
    ):
        keys, endpoint = await route_manager.routing_info(
            sub_profile, "http://example.com", mediation_record
        )
    assert keys == [*base_mediation_record.routing_keys, *mediation_record.routing_keys]
    assert endpoint == mediation_record.endpoint
