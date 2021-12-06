"""Dynamic loading of pluggable outbound queue engine classes."""
import logging
from typing import Optional, cast

from ....core.profile import Profile
from ....utils.classloader import ClassLoader
from .base import BaseOutboundQueue, OutboundQueueConfigurationError


LOGGER = logging.getLogger(__name__)


def get_outbound_queue(root_profile: Profile) -> Optional[BaseOutboundQueue]:
    """Given settings, return instantiated outbound queue class."""
    class_path = root_profile.settings.get("transport.outbound_queue")
    if not class_path:
        LOGGER.info("No outbound queue loaded")
        return None
    class_path = cast(str, class_path)
    klass = ClassLoader.load_class(class_path)
    instance = klass(root_profile)
    if not isinstance(instance, BaseOutboundQueue):
        raise OutboundQueueConfigurationError(
            "Configured class is not a subclass of BaseOutboundQueue"
        )
    return instance
