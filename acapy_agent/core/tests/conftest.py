import asyncio

import pytest


@pytest.fixture(scope="function")
def event_loop():
    """
    Custom function-scoped event loop.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
