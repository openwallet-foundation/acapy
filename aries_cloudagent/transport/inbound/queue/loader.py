"""Dynamic loading of pluggable inbound queue engine classes."""
import logging
from typing import Optional, cast

from ....core.profile import Profile
from ....utils.classloader import ClassLoader
from .base import BaseInboundQueue, InboundQueueConfigurationError


LOGGER = logging.getLogger(__name__)


def get_inbound_queue(root_profile: Profile) -> Optional[BaseInboundQueue]:
    """Given settings, return instantiated inbound queue class."""
    class_path = root_profile.settings.get("transport.inbound_queue_class")
    if not class_path:
        LOGGER.info("No inbound queue loaded")
        return None
    class_path = cast(str, class_path)
    klass = ClassLoader.load_class(class_path)
    instance = klass(root_profile)
    if not isinstance(instance, BaseInboundQueue):
        raise InboundQueueConfigurationError(
            "Configured class is not a subclass of BaseInboundQueue"
        )
    return instance
