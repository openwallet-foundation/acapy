"""Steps for upgrading the wallet to support anoncreds."""

from bdd_support.agent_backchannel_client import (
    agent_container_POST,
    async_sleep,
)
from behave import given, then


@given('"{issuer}" upgrades the wallet to anoncreds')
@then('"{issuer}" upgrades the wallet to anoncreds')
def step_impl(context, issuer):
    """Upgrade the wallet to support anoncreds."""
    agent = context.active_agents[issuer]
    agent_container_POST(
        agent["agent"],
        "/anoncreds/wallet/upgrade",
        data={},
        params={
            "wallet_name": agent["agent"].agent.wallet_name,
        },
    )

    async_sleep(2.0)
