"""Service provider implementations."""

import hashlib

from typing import Sequence, Union
from weakref import ReferenceType

from ..utils.classloader import DeferLoad
from ..utils.stats import Collector

from .base import BaseProvider, BaseSettings, BaseInjector, InjectionError


class InstanceProvider(BaseProvider):
    """Provider for a previously-created instance."""

    def __init__(self, instance):
        """Initialize the instance provider."""
        if instance is None:
            raise ValueError("Class instance binding must be non-empty")
        self._instance = instance

    def provide(self, config: BaseSettings, injector: BaseInjector):
        """Provide the object instance given a config and injector."""
        inst = self._instance
        if isinstance(inst, ReferenceType):
            inst = inst()
            if inst is None:
                raise InjectionError("Weakref instance expired")
        return inst


class ClassProvider(BaseProvider):
    """Provider for a particular class."""

    class Inject:
        """A class for passing injected arguments to the constructor."""

        def __init__(self, base_cls: type):
            """Initialize the injected argument."""
            self.base_class = base_cls

    def __init__(
        self,
        instance_cls: Union[str, type],
        *ctor_args,
        init_method: str = None,
        **ctor_kwargs
    ):
        """Initialize the class provider."""
        self._ctor_args = ctor_args
        self._ctor_kwargs = ctor_kwargs
        self._init_method = init_method
        if isinstance(instance_cls, str):
            instance_cls = DeferLoad(instance_cls)
        self._instance_cls = instance_cls

    def provide(self, config: BaseSettings, injector: BaseInjector):
        """Provide the object instance given a config and injector."""
        args = []
        for arg in self._ctor_args:
            if isinstance(arg, ClassProvider.Inject):
                arg = injector.inject(arg.base_class)
            elif isinstance(arg, ReferenceType):
                arg = arg()
                if arg is None:
                    raise InjectionError("Weakref instance expired")
            args.append(arg)
        kwargs = {}
        for arg_name, arg in self._ctor_kwargs.items():
            if isinstance(arg, ClassProvider.Inject):
                arg = injector.inject(arg.base_class)
            elif isinstance(arg, ReferenceType):
                arg = arg()
                if arg is None:
                    raise InjectionError("Weakref instance expired")
            kwargs[arg_name] = arg
        instance = (self._instance_cls)(*args, **kwargs)
        if self._init_method:
            getattr(instance, self._init_method)()
        return instance


class CachedProvider(BaseProvider):
    """Cache the result of another provider."""

    def __init__(self, provider: BaseProvider, unique_settings_keys: tuple = ()):
        """Initialize the cached provider instance."""
        if not provider:
            raise ValueError("Cache provider input must not be empty.")
        self._instances = {}
        self._provider = provider
        self._unique_settings_keys = unique_settings_keys

    def provide(self, config: BaseSettings, injector: BaseInjector):
        """
        Provide the object instance given a config and injector.

        Instances are cached keyed on a SHA256 digest of the relevant subset
        of settings.
        """
        # MTODO: how to handle changes in the config?
        instance_vals = {key: config.get(key) for key in self._unique_settings_keys}
        instance_key = hashlib.sha256(str(instance_vals).encode()).hexdigest()
        if not self._instances.get(instance_key):
            self._instances[instance_key] = self._provider.provide(config, injector)

        return self._instances[instance_key]


class StatsProvider(BaseProvider):
    """Add statistics to the results of another provider."""

    def __init__(
        self,
        provider: BaseProvider,
        methods: Sequence[str],
        *,
        ignore_missing: bool = True
    ):
        """Initialize the statistics provider instance."""
        if not provider:
            raise ValueError("Stats provider input must not be empty.")
        self._provider = provider
        self._methods = methods
        self._ignore_missing = ignore_missing

    def provide(self, config: BaseSettings, injector: BaseInjector):
        """Provide the object instance given a config and injector."""
        instance = self._provider.provide(config, injector)
        if self._methods:
            collector: Collector = injector.inject_or(Collector)
            if collector:
                collector.wrap(
                    instance, self._methods, ignore_missing=self._ignore_missing
                )
        return instance
