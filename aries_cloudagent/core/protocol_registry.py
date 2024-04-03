"""Handle registration and publication of supported protocols."""

from dataclasses import dataclass
import logging

from typing import Any, Dict, Mapping, Optional, Sequence, Union

from ..config.injection_context import InjectionContext
from ..utils.classloader import ClassLoader, DeferLoad
from ..messaging.message_type import MessageType, MessageVersion, ProtocolIdentifier

from .error import ProtocolMinorVersionNotSupported, ProtocolDefinitionValidationError

LOGGER = logging.getLogger(__name__)


@dataclass
class VersionDefinition:
    """Version definition."""

    min: MessageVersion
    current: MessageVersion

    @classmethod
    def from_dict(cls, data: dict) -> "VersionDefinition":
        """Create a version definition from a dict."""
        return cls(
            min=MessageVersion(data["major_version"], data["minimum_minor_version"]),
            current=MessageVersion(
                data["major_version"], data["current_minor_version"]
            ),
        )


@dataclass
class ProtocolDefinition:
    """Protocol metadata used to register and resolve message types."""

    ident: ProtocolIdentifier
    min: MessageVersion
    current: MessageVersion
    controller: Optional[str] = None

    @property
    def minor_versions_supported(self) -> bool:
        """Accessor for whether minor versions are supported."""
        return bool(self.current.minor >= 1 and self.current.minor >= self.min.minor)

    def __post_init__(self):
        """Post-init hook."""
        if self.min.major != self.current.major:
            raise ProtocolDefinitionValidationError(
                f"Major version mismatch: {self.min.major} != {self.current.major}"
            )
        if self.min.minor > self.current.minor:
            raise ProtocolDefinitionValidationError(
                f"Minimum minor version greater than current minor version: "
                f"{self.min.minor} > {self.current.minor}"
            )


class ProtocolRegistry:
    """Protocol registry for indexing message families."""

    def __init__(self):
        """Initialize a `ProtocolRegistry` instance."""

        self._definitions: Dict[str, ProtocolDefinition] = {}
        self._type_to_message_cls: Dict[str, Union[DeferLoad, type]] = {}

        # Mapping[protocol identifier, controller module path]
        self._controllers = {}

    @property
    def protocols(self) -> Sequence[str]:
        """Accessor for a list of all message protocols."""
        return [
            str(definition.ident.with_version((definition.min.major, minor)))
            for definition in self._definitions.values()
            for minor in range(definition.min.minor, definition.current.minor + 1)
        ]

    @property
    def message_types(self) -> Sequence[str]:
        """Accessor for a list of all message types."""
        return tuple(self._type_to_message_cls.keys())

    def protocols_matching_query(self, query: str) -> Sequence[str]:
        """Return a list of message protocols matching a query string."""
        all_types = self.protocols
        result = None

        if query == "*" or query is None:
            result = all_types
        elif query:
            if query.endswith("*"):
                match = query[:-1]
                result = tuple(k for k in all_types if k.startswith(match))
            elif query in all_types:
                result = (query,)
        return result or ()

    def register_message_types(
        self,
        typeset: Mapping[str, Union[str, type]],
        version_definition: Optional[Union[dict[str, Any], VersionDefinition]] = None,
    ):
        """Add new supported message types.

        Args:
            typesets: Mappings of message types to register
            version_definition: Optional version definition dict

        """
        if version_definition is not None and isinstance(version_definition, dict):
            version_definition = VersionDefinition.from_dict(version_definition)

        definitions_to_add = {}
        type_to_message_cls_to_add = {}

        for message_type, message_cls in typeset.items():
            parsed = MessageType.from_str(message_type)
            protocol = ProtocolIdentifier.from_message_type(parsed)
            if protocol.stem in definitions_to_add:
                definition = definitions_to_add[protocol.stem]
            elif protocol.stem in self._definitions:
                definition = self._definitions[protocol.stem]
            else:
                if version_definition:
                    definition = ProtocolDefinition(
                        ident=protocol,
                        min=version_definition.min,
                        current=version_definition.current,
                    )
                else:
                    definition = ProtocolDefinition(
                        ident=protocol,
                        min=protocol.version,
                        current=protocol.version,
                    )

                definitions_to_add[protocol.stem] = definition

            if isinstance(message_cls, str):
                message_cls = DeferLoad(message_cls)

            type_to_message_cls_to_add[message_type] = message_cls

            if definition.minor_versions_supported:
                for minor_version in range(
                    definition.min.minor, definition.current.minor + 1
                ):
                    updated_type = parsed.with_version(
                        (parsed.version.major, minor_version)
                    )
                    type_to_message_cls_to_add[str(updated_type)] = message_cls

        self._type_to_message_cls.update(type_to_message_cls_to_add)
        self._definitions.update(definitions_to_add)

    def register_controllers(self, *controller_sets):
        """Add new controllers.

        Args:
            controller_sets: Mappings of message families to coroutines

        """
        for controlset in controller_sets:
            self._controllers.update(controlset)

    def resolve_message_class(
        self, message_type: str
    ) -> Optional[Union[DeferLoad, type]]:
        """Resolve a message_type to a message class.

        Given a message type identifier, this method
        returns the corresponding registered message class.

        Args:
            message_type: Message type to resolve

        Returns:
            The resolved message class

        """
        if (message_cls := self._type_to_message_cls.get(message_type)) is not None:
            return message_cls

        parsed = MessageType.from_str(message_type)
        protocol = ProtocolIdentifier.from_message_type(parsed)
        if definition := self._definitions.get(protocol.stem):
            if parsed.version.minor < definition.min.minor:
                raise ProtocolMinorVersionNotSupported(
                    f"Minimum supported minor version is {definition.min.minor}."
                    f" Received {parsed.version.minor}."
                )

            # This code will only be reached if the received minor version is greater
            # than our current supported version. All directly supported minor
            # versions would be returned previously.
            message_type = str(parsed.with_version(definition.current))

            if (message_cls := self._type_to_message_cls.get(message_type)) is not None:
                return message_cls

        return None

    async def prepare_disclosed(
        self, context: InjectionContext, protocols: Sequence[str]
    ):
        """Call controllers and return publicly supported message families and roles."""
        published = []
        for protocol in protocols:
            result: Dict[str, Any] = {"pid": protocol}
            if protocol in self._controllers:
                ctl_cls = self._controllers[protocol]
                if isinstance(ctl_cls, str):
                    ctl_cls = ClassLoader.load_class(ctl_cls)
                ctl_instance = ctl_cls(protocol)
                if hasattr(ctl_instance, "check_access"):
                    allowed = await ctl_instance.check_access(context)
                    if not allowed:
                        # remove from published
                        continue
                if hasattr(ctl_instance, "determine_roles"):
                    roles = await ctl_instance.determine_roles(context)
                    if roles:
                        result["roles"] = list(roles)
            published.append(result)
        return published

    def __repr__(self) -> str:
        """Return a string representation for this class."""
        return "<{}>".format(self.__class__.__name__)
