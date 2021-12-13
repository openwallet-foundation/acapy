import pytest

from .....core.in_memory import InMemoryProfile
from .....utils.classloader import ClassNotFoundError
from ..base import OutboundQueueConfigurationError
from ..loader import get_outbound_queue
from .fixtures import QueueClassValid


@pytest.fixture
def profile():
    yield InMemoryProfile.test_profile(
        settings={
            "transport.outbound_queue": "aries_cloudagent.transport.outbound.queue.tests.fixtures.QueueClassValid"
        }
    )


def test_get_outbound_queue_valid(profile):
    queue = get_outbound_queue(profile)
    assert isinstance(queue, QueueClassValid)


@pytest.mark.parametrize(
    "queue",
    [
        None,
        "",
    ],
)
def test_get_outbound_not_set(queue, profile):
    profile.settings["transport.outbound_queue"] = queue
    assert get_outbound_queue(profile) is None


def test_get_outbound_x_no_class(profile):
    profile.settings["transport.outbound_queue"] = "invalid queue class path"
    with pytest.raises(ClassNotFoundError):
        get_outbound_queue(profile)


def test_get_outbound_x_bad_instance(profile):
    profile.settings["transport.outbound_queue"] = (
        "aries_cloudagent.transport.outbound.queue.tests.fixtures."
        "QueueClassNoBaseClass"
    )
    with pytest.raises(OutboundQueueConfigurationError):
        get_outbound_queue(profile)
