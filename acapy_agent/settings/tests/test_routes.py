"""Test settings routes."""

# pylint: disable=redefined-outer-name

import pytest
import pytest_asyncio

from ...admin.request_context import AdminRequestContext
from ...multitenant.base import BaseMultitenantManager
from ...multitenant.manager import MultitenantManager
from ...tests import mock
from ...utils.testing import create_test_profile
from .. import routes as test_module


@pytest.fixture
def mock_response():
    json_response = mock.MagicMock()
    temp_value = test_module.web.json_response
    test_module.web.json_response = json_response
    yield json_response
    test_module.web.json_response = temp_value


@pytest_asyncio.fixture
async def profile():
    profile = await create_test_profile()
    yield profile


@pytest_asyncio.fixture
async def admin_profile():
    profile = await create_test_profile(
        settings={
            "admin.admin_api_key": "secret-key",
        }
    )
    yield profile


@pytest.mark.asyncio
async def test_get_profile_settings(mock_response, admin_profile, profile):
    admin_profile.settings.update(
        {
            "admin.admin_client_max_request_size": 1,
            "debug.auto_respond_credential_offer": True,
            "debug.auto_respond_credential_request": True,
            "debug.auto_respond_presentation_proposal": True,
            "debug.auto_verify_presentation": True,
            "debug.auto_accept_invites": True,
            "debug.auto_accept_requests": True,
        }
    )
    request_dict = {
        "context": AdminRequestContext(
            profile=admin_profile,
        ),
    }
    request = mock.MagicMock(
        query={},
        json=mock.CoroutineMock(return_value={}),
        __getitem__=lambda _, k: request_dict[k],
        headers={"x-api-key": "secret-key"},
    )
    await test_module.get_profile_settings(request)
    assert mock_response.call_args[0][0] == {
        "debug.auto_respond_credential_offer": True,
        "debug.auto_respond_credential_request": True,
        "debug.auto_verify_presentation": True,
        "debug.auto_accept_invites": True,
        "debug.auto_accept_requests": True,
    }
    # Multitenant
    multi_tenant_manager = MultitenantManager(profile)
    profile.context.injector.bind_instance(
        BaseMultitenantManager,
        multi_tenant_manager,
    )
    request_dict = {
        "context": AdminRequestContext(
            profile=profile,
            root_profile=profile,
            metadata={
                "wallet_id": "walletid",
                "wallet_key": "walletkey",
            },
        ),
    }
    request = mock.MagicMock(
        query={},
        json=mock.CoroutineMock(return_value={}),
        __getitem__=lambda _, k: request_dict[k],
    )
    with mock.patch.object(
        multi_tenant_manager, "get_wallet_and_profile"
    ) as get_wallet_and_profile:
        get_wallet_and_profile.return_value = (
            mock.MagicMock(
                settings={
                    "admin.admin_client_max_request_size": 1,
                    "debug.auto_respond_credential_offer": True,
                    "debug.auto_respond_credential_request": True,
                    "debug.auto_respond_presentation_proposal": True,
                    "debug.auto_verify_presentation": True,
                    "debug.auto_accept_invites": True,
                    "debug.auto_accept_requests": True,
                }
            ),
            profile,
        )
        await test_module.get_profile_settings(request)
    assert mock_response.call_args[0][0] == {
        "debug.auto_respond_credential_offer": True,
        "debug.auto_respond_credential_request": True,
        "debug.auto_verify_presentation": True,
        "debug.auto_accept_invites": True,
        "debug.auto_accept_requests": True,
        "wallet.type": "askar",
    }


@pytest.mark.asyncio
async def test_update_profile_settings(mock_response, profile):
    profile.settings.update(
        {
            "public_invites": True,
            "debug.invite_public": True,
            "debug.auto_accept_invites": True,
            "debug.auto_accept_requests": True,
            "auto_ping_connection": True,
        }
    )
    request_dict = {
        "context": AdminRequestContext(
            profile=profile,
        ),
    }
    request = mock.MagicMock(
        query={},
        json=mock.CoroutineMock(
            return_value={
                "extra_settings": {
                    "ACAPY_INVITE_PUBLIC": False,
                    "ACAPY_PUBLIC_INVITES": False,
                    "ACAPY_AUTO_ACCEPT_INVITES": False,
                    "ACAPY_AUTO_ACCEPT_REQUESTS": False,
                    "ACAPY_AUTO_PING_CONNECTION": False,
                }
            }
        ),
        __getitem__=lambda _, k: request_dict[k],
    )
    await test_module.update_profile_settings(request)
    assert mock_response.call_args[0][0] == {
        "public_invites": False,
        "debug.invite_public": False,
        "debug.auto_accept_invites": False,
        "debug.auto_accept_requests": False,
        "auto_ping_connection": False,
        "wallet.type": "askar",
    }
    # Multitenant
    multi_tenant_manager = MultitenantManager(profile)
    profile.context.injector.bind_instance(
        BaseMultitenantManager,
        multi_tenant_manager,
    )

    request_dict = {
        "context": AdminRequestContext(
            profile=profile,
            root_profile=profile,
            metadata={
                "wallet_id": "walletid",
                "wallet_key": "walletkey",
            },
        ),
    }
    request = mock.MagicMock(
        query={},
        json=mock.CoroutineMock(
            return_value={
                "extra_settings": {
                    "ACAPY_INVITE_PUBLIC": False,
                    "ACAPY_PUBLIC_INVITES": False,
                    "ACAPY_AUTO_ACCEPT_INVITES": False,
                    "ACAPY_AUTO_ACCEPT_REQUESTS": False,
                    "ACAPY_AUTO_PING_CONNECTION": False,
                }
            }
        ),
        __getitem__=lambda _, k: request_dict[k],
    )
    with (
        mock.patch.object(multi_tenant_manager, "update_wallet") as update_wallet,
        mock.patch.object(
            multi_tenant_manager, "get_wallet_and_profile"
        ) as get_wallet_and_profile,
    ):
        get_wallet_and_profile.return_value = (
            mock.MagicMock(
                settings={
                    "admin.admin_client_max_request_size": 1,
                    "debug.auto_respond_credential_offer": True,
                    "debug.auto_respond_credential_request": True,
                    "debug.auto_respond_presentation_proposal": True,
                    "debug.auto_verify_presentation": True,
                    "public_invites": False,
                    "debug.invite_public": False,
                    "debug.auto_accept_invites": False,
                    "debug.auto_accept_requests": False,
                    "auto_ping_connection": False,
                }
            ),
            profile,
        )
        update_wallet.return_value = mock.MagicMock(
            settings={
                "public_invites": False,
                "debug.invite_public": False,
                "debug.auto_accept_invites": False,
                "debug.auto_accept_requests": False,
                "auto_ping_connection": False,
            }
        )
        await test_module.update_profile_settings(request)
    assert mock_response.call_args[0][0] == {
        "public_invites": False,
        "debug.invite_public": False,
        "debug.auto_accept_invites": False,
        "debug.auto_accept_requests": False,
        "auto_ping_connection": False,
        "debug.auto_respond_credential_offer": True,
        "debug.auto_respond_credential_request": True,
        "debug.auto_verify_presentation": True,
        "wallet.type": "askar",
    }
