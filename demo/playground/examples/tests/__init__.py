# pylint: disable=redefined-outer-name

from functools import wraps
import logging
import os
import time

import pytest
import requests

AUTO_ACCEPT = "false"

FABER = os.getenv("FABER")
ALICE = os.getenv("ALICE")
ACME = os.getenv("ACME")
MULTI = os.getenv("MULTI")

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


def get(agent: str, path: str, **kwargs):
    """Get."""
    return requests.get(f"{agent}{path}", **kwargs)


def post(agent: str, path: str, **kwargs):
    """Post."""
    return requests.post(f"{agent}{path}", **kwargs)


def fail_if_not_ok(message: str):
    """Fail the current test if wrapped call fails with message."""

    def _fail_if_not_ok(func):
        @wraps(func)
        def _wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            if not response.ok:
                pytest.fail(f"{message}: {response.content}")
            return response

        return _wrapper

    return _fail_if_not_ok


def unwrap_json_response(func):
    """Unwrap a requests response object to json."""

    @wraps(func)
    def _wrapper(*args, **kwargs) -> dict:
        response = func(*args, **kwargs)
        return response.json()

    return _wrapper


class Agent:
    """Class for interacting with Agent over Admin API"""

    def __init__(self, url: str, headers=None):
        self.url = url
        self._headers = headers

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

    @unwrap_json_response
    @fail_if_not_ok("Create invitation failed")
    def create_invitation(self, json=None, **kwargs):
        """Create invitation."""
        return post(
            self.url,
            "/connections/create-invitation",
            params=kwargs,
            headers=self._headers,
            json=json,
        )

    @unwrap_json_response
    @fail_if_not_ok("Receive invitation failed")
    def receive_invite(self, invite: dict, **kwargs):
        """Receive invitation."""
        return post(
            self.url,
            "/connections/receive-invitation",
            params=kwargs,
            headers=self._headers,
            json=invite,
        )

    @unwrap_json_response
    @fail_if_not_ok("Accept invitation failed")
    def accept_invite(self, connection_id: str, **kwargs):
        """Accept invitation."""
        return post(
            self.url,
            f"/connections/{connection_id}/accept-invitation",
            params=kwargs,
            headers=self._headers,
        )

    @unwrap_json_response
    @fail_if_not_ok("Create invitation failed")
    def list_connections(self, **kwargs):
        """List connections."""
        results = get(self.url, "/connections", params=kwargs, headers=self._headers)
        return results

    @unwrap_json_response
    @fail_if_not_ok("Failed to get connection by id")
    def get_connection(self, connection_id: str, **kwargs):
        """Fetch a connection."""
        return get(
            self.url,
            f"/connections/{connection_id}",
            params=kwargs,
            headers=self._headers,
        )

    @unwrap_json_response
    @fail_if_not_ok("Failed to ping connection")
    def ping_connection(self, connection_id: str, alias: str, **kwargs):
        """ping connection."""
        return post(
            self.url,
            f"/connections/{connection_id}/send-ping",
            params=kwargs,
            headers=self._headers,
            json={"comment": f"{alias} pinging..."},
        )

    @unwrap_json_response
    @fail_if_not_ok("Failure requesting mediation")
    def request_for_mediation(self, connection_id: str, **kwargs):
        """Request mediation from mediator."""
        return post(
            self.url,
            f"/mediation/request/{connection_id}",
            params=kwargs,
            headers=self._headers,
            json={},
        )

    @unwrap_json_response
    @fail_if_not_ok("Failed to check mediation request")
    def get_mediation_request(self, mediation_id: str, **kwargs):
        """Fetch mediation request."""
        return get(
            self.url,
            f"/mediation/requests/{mediation_id}",
            params=kwargs,
            headers=self._headers,
        )

    @unwrap_json_response
    @fail_if_not_ok("Failure requesting mediation")
    def create_tenant(self, wallet_name: str, wallet_key: str, **kwargs):
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
        return post(self.url, "/multitenancy/wallet", headers={}, json=data)

    def get(self, path: str, return_json: bool = True, fail_with: str = None, **kwargs):
        """Do get to agent endpoint."""
        wrapped_get = get
        if fail_with:
            wrapped_get = fail_if_not_ok(fail_with)(wrapped_get)
        if return_json:
            wrapped_get = unwrap_json_response(wrapped_get)

        return wrapped_get(self.url, path, **kwargs)

    def post(
        self, path: str, return_json: bool = True, fail_with: str = None, **kwargs
    ):
        """Do post to agent endpoint."""
        wrapped_post = post
        if fail_with:
            wrapped_post = fail_if_not_ok(fail_with)(wrapped_post)
        if return_json:
            wrapped_post = unwrap_json_response(wrapped_post)

        return wrapped_post(self.url, path, **kwargs)
