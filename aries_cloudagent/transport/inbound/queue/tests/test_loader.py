import pytest

from .....core.in_memory import InMemoryProfile
from .....utils.classloader import ClassNotFoundError
from ..base import InboundQueueConfigurationError
from ..loader import get_inbound_queue
from .fixtures import QueueClassValid


@pytest.fixture
def profile():
    yield InMemoryProfile.test_profile(
        settings={
            "transport.inbound_queue_class": "aries_cloudagent.transport.inbound.queue.tests.fixtures.QueueClassValid"
        }
    )


def test_get_inbound_queue_valid(profile):
    queue = get_inbound_queue(profile)
    assert isinstance(queue, QueueClassValid)


@pytest.mark.parametrize(
    "queue",
    [
        None,
        "",
    ],
)
def test_get_inbound_not_set(queue, profile):
    profile.settings["transport.inbound_queue_class"] = queue
    assert get_inbound_queue(profile) is None


def test_get_inbound_x_no_class(profile):
    profile.settings["transport.inbound_queue_class"] = "invalid queue class path"
    with pytest.raises(ClassNotFoundError):
        get_inbound_queue(profile)


def test_get_inbound_x_bad_instance(profile):
    profile.settings["transport.inbound_queue_class"] = (
        "aries_cloudagent.transport.inbound.queue.tests.fixtures."
        "QueueClassNoBaseClass"
    )
    with pytest.raises(InboundQueueConfigurationError):
        get_inbound_queue(profile)
