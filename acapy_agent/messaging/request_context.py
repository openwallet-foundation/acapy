"""Request context class.

A request context provides everything required by handlers and other parts
of the system to process a message.
"""

from typing import Mapping, Optional, Type

from ..config.injection_context import InjectionContext
from ..config.injector import Injector, InjectType
from ..config.settings import Settings
from ..connections.models.conn_record import ConnRecord
from ..core.profile import Profile, ProfileSession
from ..transport.inbound.receipt import MessageReceipt
from .agent_message import AgentMessage


class RequestContext:
    """Context established by the Conductor and passed into message handlers."""

    def __init__(
        self,
        profile: Profile,
        *,
        context: Optional[InjectionContext] = None,
        settings: Optional[Mapping[str, object]] = None,
    ):
        """Initialize an instance of RequestContext."""
        self._connection_ready = False
        self._connection_record = None
        self._context = (context or profile.context).start_scope(settings)
        self._message = None
        self._message_receipt = None
        self._profile = profile

    @property
    def connection_ready(self) -> bool:
        """Accessor for the flag indicating an active connection with the sender.

        Returns:
            True if the connection is active, else False

        """
        return self._connection_ready

    @connection_ready.setter
    def connection_ready(self, active: bool):
        """Setter for the flag indicating an active connection with the sender.

        Args:
            active: The new active value

        """
        self._connection_ready = active

    @property
    def connection_record(self) -> Optional[ConnRecord]:
        """Accessor for the related connection record."""
        return self._connection_record

    @connection_record.setter
    def connection_record(self, record: ConnRecord):
        """Setter for the related connection record.

        :param record: ConnRecord:

        """
        self._connection_record = record

    @property
    def default_endpoint(self) -> str:
        """Accessor for the default agent endpoint (from agent config).

        Returns:
            The default agent endpoint

        """
        return self._context.settings.get("default_endpoint")

    @default_endpoint.setter
    def default_endpoint(self, endpoint: str):
        """Setter for the default agent endpoint (from agent config).

        Args:
            endpoint: The new default endpoint

        """
        self._context.settings["default_endpoint"] = endpoint

    @property
    def default_label(self) -> str:
        """Accessor for the default agent label (from agent config).

        Returns:
            The default label

        """
        return self._context.settings["default_label"]

    @default_label.setter
    def default_label(self, label: str):
        """Setter for the default agent label (from agent config).

        Args:
            label: The new default label

        """
        self._context.settings["default_label"] = label

    @property
    def message(self) -> AgentMessage:
        """Accessor for the deserialized message instance.

        Returns:
            This context's agent message

        """
        return self._message

    @message.setter
    def message(self, msg: AgentMessage):
        """Setter for the deserialized message instance.

        Args:
            msg: This context's new agent message

        """
        self._message = msg

    @property
    def message_receipt(self) -> MessageReceipt:
        """Accessor for the message receipt information.

        Returns:
            This context's message receipt information

        """
        return self._message_receipt

    @message_receipt.setter
    def message_receipt(self, receipt: MessageReceipt):
        """Setter for the message receipt information.

        Args:
            receipt: This context's new message receipt information

        """
        self._message_receipt = receipt

    @property
    def injector(self) -> Injector:
        """Accessor for the associated `Injector` instance."""
        return self._context.injector

    @property
    def profile(self) -> Profile:
        """Accessor for the associated `Profile` instance."""
        return self._profile

    @property
    def settings(self) -> Settings:
        """Accessor for the context settings."""
        return self._context.settings

    def session(self) -> ProfileSession:
        """Start a new interactive session with no transaction support requested."""
        return self.profile.session(self._context)

    def transaction(self) -> ProfileSession:
        """Start a new interactive session with commit and rollback support.

        If the current backend does not support transactions, then commit
        and rollback operations of the session will not have any effect.
        """
        return self.profile.transaction(self._context)

    def inject(
        self,
        base_cls: Type[InjectType],
        settings: Mapping[str, object] = None,
    ) -> InjectType:
        """Get the provided instance of a given class identifier.

        Args:
            base_cls: The base class to retrieve an instance of
            settings: An optional mapping providing configuration to the provider

        Returns:
            An instance of the base class, or None

        """
        return self._context.inject(base_cls, settings)

    def inject_or(
        self,
        base_cls: Type[InjectType],
        settings: Mapping[str, object] = None,
        default: Optional[InjectType] = None,
    ) -> Optional[InjectType]:
        """Get the provided instance of a given class identifier or default if not found.

        Args:
            base_cls: The base class to retrieve an instance of
            settings: An optional dict providing configuration to the provider
            default: default return value if no instance is found

        Returns:
            An instance of the base class, or None

        """
        return self._context.inject_or(base_cls, settings, default)

    def update_settings(self, settings: Mapping[str, object]):
        """Update the scope with additional settings."""
        self._context.update_settings(settings)

    @classmethod
    def test_context(cls, profile) -> "RequestContext":
        """Quickly set up a new request context for tests."""
        return RequestContext(profile)

    def __repr__(self) -> str:
        """Provide a human readable representation of this object.

        Returns:
            A human readable representation of this object

        """
        skip = ()
        items = (
            "{}={}".format(k, repr(v)) for k, v in self.__dict__.items() if k not in skip
        )
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
