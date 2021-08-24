import pytest


from .....config.settings import Settings
from .....utils.classloader import ClassNotFoundError
from ..base import OutboundQueueConfigurationError


from ..loader import (
    get_outbound_queue,
)

from .fixtures import QueueClassValid


def test_get_outbound_queue_valid():
    settings = Settings()
    settings["transport.outbound_queue"] = (
        "aries_cloudagent.transport.outbound.queue.tests.fixtures." "QueueClassValid"
    )
    queue = get_outbound_queue(settings)
    assert isinstance(queue, QueueClassValid)


@pytest.mark.parametrize(
    "queue",
    [
        None,
        "",
    ],
)
def test_get_outbound_not_set(queue):
    settings = Settings()
    settings["transport.outbound_queue"] = queue
    assert get_outbound_queue(settings) is None


def test_get_outbound_x_no_class():
    settings = Settings()
    settings["transport.outbound_queue"] = "invalid queue class path"
    with pytest.raises(ClassNotFoundError):
        get_outbound_queue(settings)


def test_get_outbound_x_bad_instance():
    settings = Settings()
    settings["transport.outbound_queue"] = (
        "aries_cloudagent.transport.outbound.queue.tests.fixtures."
        "QueueClassNoBaseClass"
    )
    with pytest.raises(OutboundQueueConfigurationError):
        get_outbound_queue(settings)
