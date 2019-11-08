"""Handle registration and publication of supported protocols."""

from typing import Mapping, Sequence

from ..classloader import ClassLoader
from ..config.injection_context import InjectionContext


class ProtocolRegistry:
    """Protocol registry for indexing message families."""

    def __init__(self):
        """Initialize a `ProtocolRegistry` instance."""
        self._controllers = {}
        self._typemap = {}

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

    def register_message_types(self, *typesets):
        """
        Add new supported message types.

        Args:
            typesets: Mappings of message types to register

        """
        for typeset in typesets:
            self._typemap.update(typeset)

    def register_controllers(self, *controller_sets):
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
        msg_cls = self._typemap.get(message_type)
        if isinstance(msg_cls, str):
            msg_cls = ClassLoader.load_class(msg_cls)
        return msg_cls

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
