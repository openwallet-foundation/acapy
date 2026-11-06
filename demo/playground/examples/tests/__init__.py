# pylint: disable=redefined-outer-name

import asyncio
import json
import logging
import os
from functools import wraps

import aiohttp
import pytest

AUTO_ACCEPT = "false"

FABER = os.getenv("FABER", "http://faber-agent:9011")
ALICE = os.getenv("ALICE", "http://alice-agent:9012")
ACME = os.getenv("ACME", "http://acme-agent:9013")
MULTI = os.getenv("MULTI", "http://multi-agent:9014")

# Create a named logger
logger = logging.getLogger("playground_examples")
logger.setLevel(logging.INFO)
# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
# Set the formatter for the console handler
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
)
console_handler.setFormatter(formatter)
# Add the console handler to the logger
logger.addHandler(console_handler)


class _RequestsLikeResponse:
    """Wrap aiohttp response in a simple requests-like object."""

    def __init__(self, status, body, headers):
        self.status_code = status
        self._body = body
        self.headers = headers

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    def json(self):
        return json.loads(self._body)

    @property
    def content(self):
        return self._body


async def _async_get(agent: str, path: str, **kwargs):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{agent}{path}", **kwargs) as response:
            body = await response.read()
            return _RequestsLikeResponse(response.status, body, response.headers)


async def _async_post(agent: str, path: str, **kwargs):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{agent}{path}", **kwargs) as response:
            body = await response.read()
            return _RequestsLikeResponse(response.status, body, response.headers)


async def get(agent: str, path: str, **kwargs):
    """Get."""
    return await _async_get(agent, path, **kwargs)


async def post(agent: str, path: str, **kwargs):
    """Post."""
    return await _async_post(agent, path, **kwargs)


def fail_if_not_ok(message: str):
    """Fail the current test if wrapped call fails with message."""

    def _fail_if_not_ok(func):
        @wraps(func)
        async def _async_wrapper(*args, **kwargs):
            response = await func(*args, **kwargs)
            if not response.ok:
                pytest.fail(f"{message}: {response.content}")
            return response

        return _async_wrapper

    return _fail_if_not_ok


def unwrap_json_response(func):
    """Unwrap a requests response object to json."""

    @wraps(func)
    async def _async_wrapper(*args, **kwargs) -> dict:
        response = await func(*args, **kwargs)
        return response.json()

    return _async_wrapper


class Agent:
    """Class for interacting with Agent over Admin API"""

    def __init__(self, url: str, headers=None, loop: asyncio.AbstractEventLoop = None):
        """Initialize an Agent client.

        Args:
            url: The agent's admin API URL.
            headers: Optional default headers.
            loop: Optional event loop. If not provided, the current running
                loop is used; if none is running, a new loop is created.
        """
        self.url = url
        self._headers = headers
        if loop is None:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        self._loop = loop
        self._session = aiohttp.ClientSession()

    @property
    def headers(self):
        """Accessor for the agents http headers.

        Returns:
            dict or None

        """
        return self._headers

    @headers.setter
    def headers(self, headers):
        """Setter for agent's http headers.

        Args:
            headers: dict or None

        """
        self._headers = headers

    async def close(self):
        """Close the underlying aiohttp session."""
        await self._session.close()

    async def _request(self, method: str, path: str, **kwargs):
        headers = kwargs.pop("headers", self._headers)
        async with self._session.request(
            method, f"{self.url}{path}", headers=headers, **kwargs
        ) as response:
            body = await response.read()
            return _RequestsLikeResponse(response.status, body, response.headers)

    @unwrap_json_response
    @fail_if_not_ok("Create invitation failed")
    async def create_invitation(self, json=None, **kwargs):
        """Create invitation."""
        return await self._request(
            "POST",
            "/connections/create-invitation",
            params=kwargs,
            json=json,
        )

    @unwrap_json_response
    @fail_if_not_ok("Receive invitation failed")
    async def receive_invite(self, invite: dict, **kwargs):
        """Receive invitation."""
        return await self._request(
            "POST",
            "/connections/receive-invitation",
            params=kwargs,
            json=invite,
        )

    @unwrap_json_response
    @fail_if_not_ok("Accept invitation failed")
    async def accept_invite(self, connection_id: str, **kwargs):
        """Accept invitation."""
        return await self._request(
            "POST",
            f"/connections/{connection_id}/accept-invitation",
            params=kwargs,
        )

    @unwrap_json_response
    @fail_if_not_ok("Create invitation failed")
    async def list_connections(self, **kwargs):
        """List connections."""
        return await self._request(
            "GET", "/connections", params=kwargs
        )

    @unwrap_json_response
    @fail_if_not_ok("Failed to get connection by id")
    async def get_connection(self, connection_id: str, **kwargs):
        """Fetch a connection."""
        return await self._request(
            "GET",
            f"/connections/{connection_id}",
            params=kwargs,
        )

    @unwrap_json_response
    @fail_if_not_ok("Failed to ping connection")
    async def ping_connection(self, connection_id: str, alias: str, **kwargs):
        """ping connection."""
        return await self._request(
            "POST",
            f"/connections/{connection_id}/send-ping",
            params=kwargs,
            json={"comment": f"{alias} pinging..."},
        )

    @unwrap_json_response
    @fail_if_not_ok("Failure requesting mediation")
    async def request_for_mediation(self, connection_id: str, **kwargs):
        """Request mediation from mediator."""
        return await self._request(
            "POST",
            f"/mediation/request/{connection_id}",
            params=kwargs,
            json={},
        )

    @unwrap_json_response
    @fail_if_not_ok("Failed to check mediation request")
    async def get_mediation_request(self, mediation_id: str, **kwargs):
        """Fetch mediation request."""
        return await self._request(
            "GET",
            f"/mediation/requests/{mediation_id}",
            params=kwargs,
        )

    @unwrap_json_response
    @fail_if_not_ok("Failure requesting mediation")
    async def create_tenant(self, wallet_name: str, wallet_key: str, **kwargs):
        """Create a tenant in multitenanted acapy."""
        data = {
            "key_management_mode": "managed",
            "wallet_dispatch_type": "default",
            "wallet_name": wallet_name,
            "wallet_key": wallet_key,
            "label": wallet_name,
            "wallet_type": "askar",
            "wallet_webhook_urls": [],
        }
        # multi-agent has no security for base wallet, just call multitenancy/wallet
        # to create a new tenant
        return await self._request(
            "POST", "/multitenancy/wallet", headers={}, json=data
        )

    async def get(
        self, path: str, return_json: bool = True, fail_with: str = None, **kwargs
    ):
        """Do get to agent endpoint."""
        wrapped_get = get
        if fail_with:
            wrapped_get = fail_if_not_ok(fail_with)(wrapped_get)
        if return_json:
            wrapped_get = unwrap_json_response(wrapped_get)

        return await wrapped_get(self.url, path, **kwargs)

    async def post(
        self, path: str, return_json: bool = True, fail_with: str = None, **kwargs
    ):
        """Do post to agent endpoint."""
        wrapped_post = post
        if fail_with:
            wrapped_post = fail_if_not_ok(fail_with)(wrapped_post)
        if return_json:
            wrapped_post = unwrap_json_response(wrapped_post)

        return await wrapped_post(self.url, path, **kwargs)
