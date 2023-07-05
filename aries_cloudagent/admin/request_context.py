"""
Admin request context class.

A request context provided by the admin server to admin route handlers.
"""

from typing import Mapping, Optional, Type

from ..core.profile import Profile, ProfileSession
from ..config.injector import Injector, InjectionError, InjectType
from ..config.injection_context import InjectionContext
from ..config.settings import Settings
from ..utils.classloader import DeferLoad

IN_MEM = DeferLoad("aries_cloudagent.core.in_memory.InMemoryProfile")


class AdminRequestContext:
    """Context established by the Conductor and passed into message handlers."""

    def __init__(
        self,
        profile: Profile,
        *,
        context: InjectionContext = None,
        settings: Mapping[str, object] = None,
        root_profile: Profile = None,
        metadata: dict = None
    ):
        """Initialize an instance of AdminRequestContext."""
        self._context = (context or profile.context).start_scope("admin", settings)
        self._profile = profile
        self._root_profile = root_profile
        self._metadata = metadata

    @property
    def injector(self) -> Injector:
        """Accessor for the associated `Injector` instance."""
        return self._context.injector

    @property
    def profile(self) -> Profile:
        """Accessor for the associated `Profile` instance."""
        return self._profile

    @property
    def root_profile(self) -> Optional[Profile]:
        """Accessor for the associated root_profile instance."""
        return self._root_profile

    @property
    def metadata(self) -> dict:
        """Accessor for the associated metadata."""
        return self._metadata

    @property
    def settings(self) -> Settings:
        """Accessor for the context settings."""
        return self._context.settings

    def session(self) -> ProfileSession:
        """Start a new interactive session with no transaction support requested."""
        return self.profile.session(self._context)

    def transaction(self) -> ProfileSession:
        """
        Start a new interactive session with commit and rollback support.

        If the current backend does not support transactions, then commit
        and rollback operations of the session will not have any effect.
        """
        return self.profile.transaction(self._context)

    def inject(
        self,
        base_cls: Type[InjectType],
        settings: Mapping[str, object] = None,
    ) -> InjectType:
        """
        Get the provided instance of a given class identifier.

        Args:
            cls: The base class to retrieve an instance of
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
        """
        Get the provided instance of a given class identifier or default if not found.

        Args:
            base_cls: The base class to retrieve an instance of
            settings: An optional dict providing configuration to the provider
            default: default return value if no instance is found

        Returns:
            An instance of the base class, or None

        """
        return self._context.inject_or(base_cls, settings, default)

    def update_settings(self, settings: Mapping[str, object]):
        """Update the current scope with additional settings."""
        self._context.update_settings(settings)

    @classmethod
    def test_context(
        cls, session_inject: dict = None, profile: Profile = None
    ) -> "AdminRequestContext":
        """Quickly set up a new admin request context for tests."""
        ctx = AdminRequestContext(profile or IN_MEM.resolved.test_profile())
        setattr(
            ctx, "session_inject", dict() if session_inject is None else session_inject
        )
        setattr(ctx, "session", ctx._test_session)
        return ctx

    def _test_session(self) -> ProfileSession:
        session = self.profile.session(self._context)

        def _inject(base_cls):
            if session._active and base_cls in self.session_inject:
                ret = self.session_inject[base_cls]
                if ret is None:
                    raise InjectionError(
                        "No instance provided for class: {}".format(base_cls.__name__)
                    )
                return ret
            return session._context.injector.inject(base_cls)

        def _inject_or(base_cls, default=None):
            if session._active and base_cls in self.session_inject:
                ret = self.session_inject[base_cls]
                if ret is None:
                    ret = default
                return ret
            return session._context.injector.inject_or(base_cls, default)

        setattr(session, "inject", _inject)
        setattr(session, "inject_or", _inject_or)
        return session

    def __repr__(self) -> str:
        """
        Provide a human readable representation of this object.

        Returns:
            A human readable representation of this object

        """
        skip = ("session",)
        items = (
            "{}={}".format(k, repr(v))
            for k, v in self.__dict__.items()
            if k not in skip
        )
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
