"""Service provider implementations."""

import logging

from typing import Sequence, Union

from ..utils.classloader import ClassLoader
from ..utils.stats import Collector

from .base import BaseProvider, BaseSettings, BaseInjector

LOGGER = logging.getLogger(__name__)

class InstanceProvider(BaseProvider):
    """Provider for a previously-created instance."""

    def __init__(self, instance):
        """Initialize the instance provider."""
        if not instance:
            raise ValueError("Class instance binding must be non-empty")
        self._instance = instance

    async def provide(self, config: BaseSettings, injector: BaseInjector):
        """Provide the object instance given a config and injector."""
        return self._instance


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
        async_init: str = None,
        **ctor_kwargs
    ):
        """Initialize the class provider."""
        self._async_init = async_init
        self._ctor_args = ctor_args
        self._ctor_kwargs = ctor_kwargs
        self._instance_cls = instance_cls

    async def provide(self, config: BaseSettings, injector: BaseInjector):
        """Provide the object instance given a config and injector."""
        instance_cls = self._instance_cls
        if isinstance(instance_cls, str):
            instance_cls = ClassLoader.load_class(instance_cls)
            self._instance_cls = instance_cls
        args = []
        for arg in self._ctor_args:
            if isinstance(arg, self.Inject):
                arg = await injector.inject(arg.base_class)
            args.append(arg)
        kwargs = {}
        for arg_name, arg in self._ctor_kwargs.items():
            if isinstance(arg, self.Inject):
                arg = await injector.inject(arg.base_class)
            kwargs[arg_name] = arg
        instance = instance_cls(*args, **kwargs)
        if self._async_init:
            await getattr(instance, self._async_init)()
        return instance


class CachedProvider(BaseProvider):
    """Cache the result of another provider."""

    def __init__(self, provider: BaseProvider):
        """Initialize the cached provider instance."""
        if not provider:
            raise ValueError("Cache provider input must not be empty.")
        self._instance = None
        self._provider = provider

    async def provide(self, config: BaseSettings, injector: BaseInjector):
        """Provide the object instance given a config and injector."""
        if not self._instance:
            self._instance = await self._provider.provide(config, injector)
        return self._instance


class DynamicProvider(BaseProvider):
    """Cache the result of another provider."""

    def __init__(self, provider: BaseProvider, key: str):
        """
        Initialize the cached provider instance.

        Args:
            key: Key used to identifier which stored instance should be
            provided.
        """
        if not provider:
            raise ValueError("Dynamic provider input must not be empty.")

        # Maps: `instance_id -> instance`
        self._instances = {}
        self._provider = provider
        self._configs = {}
        self._requested_instance = None
        self._config_key = key

    async def provide(self,
                      config: BaseSettings,
                      injector: BaseInjector,
                      id: str = None):
        """Provide the object instance given a config and injector."""
        if id:
            instance_id = id
            if instance_id not in self._instances.keys():
                raise ValueError(f"Requested instance not in cache.")
        #  FIXME: make generic or should it always depend on the  wallet?!
        elif "wallet.id" in config:
            instance_id = config.get_value("wallet.id")
            # If the requested instance is not in instances create it.
            if instance_id not in self._instances.keys():
                self._instances[instance_id] = await self._provider.provide(
                    config, injector)
        else:
            # If no specific instance is provided we either are not in
            # multitenant agent or want to use base wallet.
            # FIXME: How to check if setting id was just forgotten?
            instance_id = config.get(self._config_key)
            if instance_id not in self._instances.keys():
                self._instances[instance_id] = await self._provider.provide(
                    config, injector)
        return self._instances[instance_id]


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

    async def provide(self, config: BaseSettings, injector: BaseInjector):
        """Provide the object instance given a config and injector."""
        instance = await self._provider.provide(config, injector)
        if self._methods:
            collector: Collector = await injector.inject(Collector, required=False)
            if collector:
                collector.wrap(
                    instance, self._methods, ignore_missing=self._ignore_missing
                )
        return instance
