"""Dynamic loading of pluggable outbound queue engine classes."""
import importlib

from ....config.settings import Settings
from ....core.error import BaseError


def get_outbound_queue(settings: Settings):
    """Given ``settings``, return instantiated outbound queue class.

    Raises `OutboundQueueConfigurationError` in the case there is a
    problem with the configuration.
    """
    connection, prefix, class_location = (
        settings.get("transport.outbound_queue"),
        settings.get("transport.outbound_queue_prefix"),
        settings.get("transport.outbound_queue_class"),
    )
    if not connection:
        return None
    klass = get_class(class_location)
    protocol, _, __ = get_connection_parts(connection)
    class_protocol = getattr(klass, "protocol", None)
    if class_protocol != protocol:
        raise OutboundQueueConfigurationError(
            f"Queue configuration '{protocol}' not matched with protocol "
            f"'{class_protocol}'"
        )
    return klass(connection=connection, prefix=prefix)


def get_class(dotpath: str):
    """Dynamically loads class from ``dotpath``.

    Returns the Python class. The ``dotpath`` should specify a Python
    module, followed by a colon (:), followed by the name of the Python
    class.

    Raises `OutboundQueueConfigurationError` in the case there is a
    problem with the configuration.
    """
    try:
        module_path, class_name = dotpath.split(":")
    except ValueError:
        raise OutboundQueueConfigurationError(f"Malformed input '{dotpath}'")
    try:
        module = importlib.import_module(module_path)
    except ImportError:
        raise OutboundQueueConfigurationError(f"Module not found at '{module_path}'")
    try:
        klass = getattr(module, class_name)
    except AttributeError:
        raise OutboundQueueConfigurationError(f"Class not found at '{dotpath}'")
    if "BaseOutboundQueue" not in [baseclass.__name__ for baseclass in klass.mro()]:
        raise OutboundQueueConfigurationError(
            f"Class '{dotpath}' does not inherit from BaseOutboundQueue"
        )
    if not getattr(klass, "protocol", None):
        raise OutboundQueueConfigurationError(
            f"Custom Outbound Queue class '{dotpath}' requires a defined "
            f"'protocol' attribute"
        )
    return klass


def get_connection_parts(connection: str):
    """Given ``connection``, return a tuple of protocol, host, and port.

    The ``connection`` argument should be a string in the following form:
        [protocol]://[hostname]:[port]

    Raises `OutboundQueueConfigurationError` in the case there is a
    problem with the configuration.
    """
    try:
        protocol, host_and_port = connection.split("://")
        host, port = host_and_port.split(":")
        return protocol, host, port
    except ValueError:
        raise OutboundQueueConfigurationError(
            "Queue configuration required: '[protocol]://[hostname]:[port]'"
        )


class OutboundQueueConfigurationError(BaseError):
    """An error with the queue configuration."""

    def __init__(self, message):
        """Initialize the exception instance."""
        super().__init__(message)
