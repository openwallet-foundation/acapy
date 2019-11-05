"""Sane defaults for known message definitions."""

from .classloader import ClassLoader, ModuleLoadError

from .messaging.protocol_registry import ProtocolRegistry

from .messaging.presentations.message_types import (
    MESSAGE_TYPES as PRESENTATION_MESSAGES,
)
from .messaging.credentials.message_types import MESSAGE_TYPES as CREDENTIAL_MESSAGES
from .messaging.issue_credential.v1_0.message_types import (
    MESSAGE_TYPES as V10_ISSUE_CREDENTIAL_MESSAGES,
)
from .messaging.present_proof.v1_0.message_types import (
    MESSAGE_TYPES as V10_PRESENT_PROOF_MESSAGES,
)


def default_protocol_registry() -> ProtocolRegistry:
    """Protocol registry for default message types."""
    registry = ProtocolRegistry()

    registry.register_message_types(
        PRESENTATION_MESSAGES,
        V10_PRESENT_PROOF_MESSAGES,
        CREDENTIAL_MESSAGES,
        V10_ISSUE_CREDENTIAL_MESSAGES,
    )

    packages = ClassLoader.scan_subpackages("aries_cloudagent.protocols")
    for pkg in packages:
        try:
            mod = ClassLoader.load_module(pkg + ".message_types")
        except ModuleLoadError:
            continue
        if hasattr(mod, "MESSAGE_TYPES"):
            registry.register_message_types(mod.MESSAGE_TYPES)
        if hasattr(mod, "CONTROLLERS"):
            registry.register_controllers(mod.CONTROLLERS)

    return registry
