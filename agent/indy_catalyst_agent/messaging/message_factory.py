"""Handle identification of message types and instantiation of message classes."""

from typing import Coroutine, Sequence

from ..classloader import ClassLoader
from ..config.injection_context import InjectionContext


class MessageFactory:
    """Message factory for deserializing messages."""

    def __init__(self):
        """Initialize a MessageFactory instance."""
        self._role_checks = []
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
    def role_determiners(self) -> Sequence[Coroutine]:
        """Accessor for a list of all message determiner functions."""
        return tuple(self._role_checks)

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
            *typesets: Mappings of message types to register

        """
        for typeset in typesets:
            self._typemap.update(typeset)

    def register_role_determiners(self, *determiners):
        """
        Add new role determiners.

        Args:
            *determiners: Coroutines to call to determine supported roles

        """
        self._role_checks.extend(determiners)

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

    async def determine_roles(
        self, context: InjectionContext, protocols: Sequence[str]
    ):
        """Call role determiners to obtain the currently supported roles."""
        roles = {}
        for routine in self._role_checks:
            result = await routine(context, protocols)
            if result:
                for k in result:
                    if k in roles:
                        roles[k].update(result[k])
                    else:
                        roles[k] = set(result[k])
        return {k: list(v) for k, v in roles.items()}

    def __repr__(self) -> str:
        """Return a string representation for this class."""
        return "<{}>".format(self.__class__.__name__)
