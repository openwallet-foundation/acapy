"""Test settings routes."""

# pylint: disable=redefined-outer-name

import pytest
from asynctest import mock as async_mock
from ...core.in_memory import InMemoryProfile

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
    context = profile.context
    setattr(context, "profile", profile)
    request_dict = {
        "context": context,
    }
    request = async_mock.MagicMock(
        query={},
        json=async_mock.CoroutineMock(return_value={}),
        __getitem__=lambda _, k: request_dict[k],
    )
    await test_module.get_profile_settings(request)
    assert mock_response.call_args[0][0] == {
        "admin.admin_client_max_request_size": 1,
        "debug.auto_respond_credential_offer": True,
        "debug.auto_respond_credential_request": True,
        "debug.auto_respond_presentation_proposal": True,
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
    context = profile.context
    setattr(context, "profile", profile)
    request_dict = {
        "context": context,
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
