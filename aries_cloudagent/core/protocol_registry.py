"""Handle registration and publication of supported protocols."""

import logging
import re

from typing import Mapping, Sequence

from ..config.injection_context import InjectionContext
from ..utils.classloader import ClassLoader

from .error import ProtocolMinorVersionNotSupported, ProtocolDefinitionValidationError

LOGGER = logging.getLogger(__name__)


class ProtocolRegistry:
    """Protocol registry for indexing message families."""

    def __init__(self):
        """Initialize a `ProtocolRegistry` instance."""
        self._controllers = {}
        self._typemap = {}
        self._versionmap = {}

    @property
    def protocols(self) -> Sequence[str]:
        """Accessor for a list of all message protocols."""
        prots = set()
        for message_type in self._typemap.keys():
            pos = message_type.rfind("/")
            if pos > 0:
                family = message_type[:pos]
                prots.add(family)
        return prots

    @property
    def message_types(self) -> Sequence[str]:
        """Accessor for a list of all message types."""
        return tuple(self._typemap.keys())

    @property
    def controllers(self) -> Mapping[str, str]:
        """Accessor for a list of all protocol controller functions."""
        return self._controllers.copy()

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

    def parse_type_string(self, message_type):
        """Parse message type string and return dict with info."""
        tokens = message_type.split("/")
        protocol_name = tokens[-3]
        version_string = tokens[-2]
        message_name = tokens[-1]

        version_string_tokens = version_string.split(".")
        assert len(version_string_tokens) == 2

        return {
            "protocol_name": protocol_name,
            "message_name": message_name,
            "major_version": int(version_string_tokens[0]),
            "minor_version": int(version_string_tokens[1]),
        }

    def create_msg_types_for_minor_version(self, typesets, version_definition):
        """
        Return mapping of message type to module path for minor versions.

        Args:
            typesets: Mappings of message types to register
            version_definition: Optional version definition dict

        Returns:
            Typesets mapping

        """
        updated_typeset = {}
        curr_minor_version = version_definition["current_minor_version"]
        min_minor_version = version_definition["minimum_minor_version"]
        major_version = version_definition["major_version"]
        if curr_minor_version >= min_minor_version:
            for version_index in range(min_minor_version, curr_minor_version + 1):
                to_check = f"{str(major_version)}.{str(version_index)}"
                updated_typeset.update(
                    self._get_updated_typeset_dict(typesets, to_check, updated_typeset)
                )
        else:
            raise ProtocolDefinitionValidationError(
                "min_minor_version is greater than curr_minor_version for the"
                f" following typeset: {str(typesets)}"
            )
        return (updated_typeset,)

    def _get_updated_typeset_dict(self, typesets, to_check, updated_typeset) -> dict:
        for typeset in typesets:
            for msg_type_string, module_path in typeset.items():
                updated_msg_type_string = re.sub(
                    r"(\d+\.)?(\*|\d+)", to_check, msg_type_string
                )
                updated_typeset[updated_msg_type_string] = module_path
        return updated_typeset

    def _message_type_check_for_minor_verssion(self, version_definition) -> bool:
        if not version_definition:
            return False
        curr_minor_version = version_definition["current_minor_version"]
        min_minor_version = version_definition["minimum_minor_version"]
        return bool(curr_minor_version >= 1 and curr_minor_version >= min_minor_version)

    def _create_and_register_updated_typesets(self, typesets, version_definition):
        updated_typesets = self.create_msg_types_for_minor_version(
            typesets, version_definition
        )
        update_flag = False
        for typeset in updated_typesets:
            if typeset:
                self._typemap.update(typeset)
                update_flag = True
        if update_flag:
            return updated_typesets
        else:
            return None

    def _update_version_map(self, message_type_string, module_path, version_definition):
        parsed_type_string = self.parse_type_string(message_type_string)

        if version_definition["major_version"] not in self._versionmap:
            self._versionmap[version_definition["major_version"]] = []

        self._versionmap[version_definition["major_version"]].append(
            {
                "parsed_type_string": parsed_type_string,
                "version_definition": version_definition,
                "message_module": module_path,
            }
        )

    def register_message_types(self, *typesets, version_definition=None):
        """
        Add new supported message types.

        Args:
            typesets: Mappings of message types to register
            version_definition: Optional version definition dict

        """

        # Maintain support for versionless protocol modules
        updated_typesets = None
        minor_versions_supported = self._message_type_check_for_minor_verssion(
            version_definition
        )
        if not minor_versions_supported:
            for typeset in typesets:
                self._typemap.update(typeset)

        # Track versioned modules for version routing
        if version_definition:
            # create updated typesets for minor versions and register them
            if minor_versions_supported:
                updated_typesets = self._create_and_register_updated_typesets(
                    typesets, version_definition
                )
            if updated_typesets:
                typesets = updated_typesets
            for typeset in typesets:
                for message_type_string, module_path in typeset.items():
                    self._update_version_map(
                        message_type_string, module_path, version_definition
                    )

    def register_controllers(self, *controller_sets, version_definition=None):
        """
        Add new controllers.

        Args:
            controller_sets: Mappings of message families to coroutines

        """
        for controlset in controller_sets:
            self._controllers.update(controlset)

    def resolve_message_class(self, message_type: str) -> type:
        """
        Resolve a message_type to a message class.

        Given a message type identifier, this method
        returns the corresponding registered message class.

        Args:
            message_type: Message type to resolve

        Returns:
            The resolved message class

        """

        # Try and retrieve from direct mapping
        msg_cls = self._typemap.get(message_type)
        if isinstance(msg_cls, str):
            return ClassLoader.load_class(msg_cls)

        # Support registered modules (not path as string)
        elif msg_cls:
            return msg_cls

        # Try and route via min/maj version matching
        if not msg_cls:
            parsed_type_string = self.parse_type_string(message_type)
            major_version = parsed_type_string["major_version"]

            version_supported_protos = self._versionmap.get(major_version)
            if not version_supported_protos:
                return None

            for proto in version_supported_protos:
                if (
                    proto["parsed_type_string"]["protocol_name"]
                    == parsed_type_string["protocol_name"]
                    and proto["parsed_type_string"]["message_name"]
                    == parsed_type_string["message_name"]
                ):
                    if (
                        parsed_type_string["minor_version"]
                        < proto["version_definition"]["minimum_minor_version"]
                    ):
                        raise ProtocolMinorVersionNotSupported(
                            "Minimum supported minor version is "
                            + f"{proto['version_definition']['minimum_minor_version']}."
                            + f" Received {parsed_type_string['minor_version']}."
                        )

                    if isinstance(proto["message_module"], str):
                        return ClassLoader.load_class(msg_cls)
                    elif proto["message_module"]:
                        return proto["message_module"]

        return None

    async def prepare_disclosed(
        self, context: InjectionContext, protocols: Sequence[str]
    ):
        """Call controllers and return publicly supported message families and roles."""
        published = []
        for protocol in protocols:
            result = {"pid": protocol}
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
