"""Core utilities and constants."""

import inspect
import os
import re

from typing import Optional, Tuple

from ..cache.base import BaseCache
from ..core.profile import Profile
from ..messaging.agent_message import AgentMessage
from ..utils.classloader import ClassLoader

from .error import ProtocolMinorVersionNotSupported, ProtocolDefinitionValidationError

CORE_EVENT_PREFIX = "acapy::core::"
STARTUP_EVENT_TOPIC = CORE_EVENT_PREFIX + "startup"
STARTUP_EVENT_PATTERN = re.compile(f"^{STARTUP_EVENT_TOPIC}?$")
SHUTDOWN_EVENT_TOPIC = CORE_EVENT_PREFIX + "shutdown"
SHUTDOWN_EVENT_PATTERN = re.compile(f"^{SHUTDOWN_EVENT_TOPIC}?$")
WARNING_DEGRADED_FEATURES = "version-with-degraded-features"
WARNING_VERSION_MISMATCH = "fields-ignored-due-to-version-mismatch"
WARNING_VERSION_NOT_SUPPORTED = "version-not-supported"


async def validate_get_response_version(
    profile: Profile, rec_version: str, msg_class: type
) -> Tuple[str, Optional[str]]:
    """
    Return a tuple with version to respond with and warnings.

    Process received version and protocol version definition,
    returns the tuple.

    Args:
        profile: Profile
        rec_version: received version from message
        msg_class: type

    Returns:
        Tuple with response version and any warnings

    """
    resp_version = rec_version
    warning = None
    version_string_tokens = rec_version.split(".")
    rec_major_version = int(version_string_tokens[0])
    rec_minor_version = int(version_string_tokens[1])
    version_definition = await get_version_def_from_msg_class(
        profile, msg_class, rec_major_version
    )
    proto_major_version = int(version_definition["major_version"])
    proto_curr_minor_version = int(version_definition["current_minor_version"])
    proto_min_minor_version = int(version_definition["minimum_minor_version"])
    if rec_minor_version < proto_min_minor_version:
        warning = WARNING_VERSION_NOT_SUPPORTED
    elif (
        rec_minor_version >= proto_min_minor_version
        and rec_minor_version < proto_curr_minor_version
    ):
        warning = WARNING_DEGRADED_FEATURES
    elif rec_minor_version > proto_curr_minor_version:
        warning = WARNING_VERSION_MISMATCH
    if proto_major_version == rec_major_version:
        if (
            proto_min_minor_version <= rec_minor_version
            and proto_curr_minor_version >= rec_minor_version
        ):
            resp_version = f"{str(proto_major_version)}.{str(rec_minor_version)}"
        elif rec_minor_version > proto_curr_minor_version:
            resp_version = f"{str(proto_major_version)}.{str(proto_curr_minor_version)}"
        elif rec_minor_version < proto_min_minor_version:
            raise ProtocolMinorVersionNotSupported(
                "Minimum supported minor version is "
                + f"{proto_min_minor_version}."
                + f" Received {rec_minor_version}."
            )
    else:
        raise ProtocolMinorVersionNotSupported(
            f"Supported major version {proto_major_version}"
            " is not same as received major version"
            f" {rec_major_version}."
        )
    return (resp_version, warning)


def get_version_from_message_type(msg_type: str) -> str:
    """Return version from provided message_type."""
    return (re.search(r"(\d+\.)?(\*|\d+)", msg_type)).group()


def get_version_from_message(msg: AgentMessage) -> str:
    """Return version from provided AgentMessage."""
    msg_type = msg._type
    return get_version_from_message_type(msg_type)


async def get_proto_default_version_from_msg_class(
    profile: Profile, msg_class: type, major_version: int = 1
) -> str:
    """Return default protocol version from version_definition."""
    version_definition = await get_version_def_from_msg_class(
        profile, msg_class, major_version
    )
    return _get_default_version_from_version_def(version_definition)


def get_proto_default_version(def_path: str, major_version: int = 1) -> str:
    """Return default protocol version from version_definition."""
    version_definition = _get_version_def_from_path(def_path, major_version)
    return _get_default_version_from_version_def(version_definition)


def _resolve_definition(search_path: str, msg_class: type) -> str:
    try:
        path = os.path.normpath(inspect.getfile(msg_class))
        path = search_path + path.rsplit(search_path, 1)[1]
        version = (re.search(r"v(\d+\_)?(\*|\d+)", path)).group()
        path = path.split(version, 1)[0]
        definition_path = (path.replace("/", ".")) + "definition"
        if ClassLoader.load_module(definition_path):
            return definition_path
    except Exception:
        # we expect some exceptions resolving paths
        pass


def _get_path_from_msg_class(msg_class: type) -> str:
    search_paths = ["aries_cloudagent", msg_class.__module__.split(".", 1)[0]]
    if os.getenv("ACAPY_HOME"):
        search_paths.insert(os.getenv("ACAPY_HOME"), 0)

    definition_path = None
    searches = 0
    while not definition_path and searches < len(search_paths):
        definition_path = _resolve_definition(search_paths[searches], msg_class)
        searches = searches + 1
    # we could throw an exception here,
    return definition_path


def _get_version_def_from_path(definition_path: str, major_version: int = 1):
    version_definition = None
    definition = ClassLoader.load_module(definition_path)
    for protocol_version in definition.versions:
        if major_version == protocol_version["major_version"]:
            version_definition = protocol_version
            break
    return version_definition


def _get_default_version_from_version_def(version_definition) -> str:
    default_major_version = version_definition["major_version"]
    default_minor_version = version_definition["current_minor_version"]
    return f"{default_major_version}.{default_minor_version}"


async def get_version_def_from_msg_class(
    profile: Profile, msg_class: type, major_version: int = 1
):
    """Return version_definition of a protocol from msg_class."""
    cache = profile.inject_or(BaseCache)
    version_definition = None
    if cache:
        version_definition = await cache.get(
            f"version_definition::{str(msg_class).lower()}"
        )
        if version_definition:
            return version_definition
    definition_path = _get_path_from_msg_class(msg_class)
    version_definition = _get_version_def_from_path(definition_path, major_version)
    if not version_definition:
        raise ProtocolDefinitionValidationError(
            f"Unable to load protocol version_definition for {str(msg_class)}"
        )
    if cache:
        await cache.set(
            f"version_definition::{str(msg_class).lower()}", version_definition
        )
    return version_definition
