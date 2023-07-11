"""Test settings routes."""

# pylint: disable=redefined-outer-name

import pytest
from asynctest import mock as async_mock

from ...admin.request_context import AdminRequestContext
from ...core.in_memory import InMemoryProfile
from ...multitenant.base import BaseMultitenantManager
from ...multitenant.manager import MultitenantManager

from .. import routes as test_module


@pytest.fixture
def mock_response():
    json_response = async_mock.MagicMock()
    temp_value = test_module.web.json_response
    test_module.web.json_response = json_response
    yield json_response
    test_module.web.json_response = temp_value


@pytest.mark.asyncio
async def test_get_profile_settings(mock_response):
    profile = InMemoryProfile.test_profile()
    profile.settings.update(
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
            profile=profile,
        ),
    }
    request = async_mock.MagicMock(
        query={},
        json=async_mock.CoroutineMock(return_value={}),
        __getitem__=lambda _, k: request_dict[k],
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
    profile = InMemoryProfile.test_profile()
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
    request = async_mock.MagicMock(
        query={},
        json=async_mock.CoroutineMock(return_value={}),
        __getitem__=lambda _, k: request_dict[k],
    )
    with async_mock.patch.object(
        multi_tenant_manager, "get_wallet_and_profile"
    ) as get_wallet_and_profile:
        get_wallet_and_profile.return_value = (
            async_mock.MagicMock(
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
    }


@pytest.mark.asyncio
async def test_update_profile_settings(mock_response):
    profile = InMemoryProfile.test_profile()
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
    request = async_mock.MagicMock(
        query={},
        json=async_mock.CoroutineMock(
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
    }
    # Multitenant
    profile = InMemoryProfile.test_profile()
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
    request = async_mock.MagicMock(
        query={},
        json=async_mock.CoroutineMock(
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
    with async_mock.patch.object(
        multi_tenant_manager, "update_wallet"
    ) as update_wallet, async_mock.patch.object(
        multi_tenant_manager, "get_wallet_and_profile"
    ) as get_wallet_and_profile:
        get_wallet_and_profile.return_value = (
            async_mock.MagicMock(
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
        update_wallet.return_value = async_mock.MagicMock(
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
    }
