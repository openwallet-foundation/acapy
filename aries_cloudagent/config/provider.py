"""Service provider implementations."""

from typing import Sequence, Union

from ..utils.classloader import ClassLoader
from ..utils.stats import Collector

from .base import BaseProvider, BaseSettings, BaseInjector


class InstanceProvider(BaseProvider):
    """Provider for a previously-created instance."""

    def __init__(self, instance):
        """Initialize the instance provider."""
        if not instance:
            raise ValueError("Class instance binding must be non-empty")
        self._instance = instance

    def provide(self, config: BaseSettings, injector: BaseInjector):
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
        init_method: str = None,
        **ctor_kwargs
    ):
        """Initialize the class provider."""
        self._ctor_args = ctor_args
        self._ctor_kwargs = ctor_kwargs
        self._init_method = init_method
        self._instance_cls = instance_cls

    def provide(self, config: BaseSettings, injector: BaseInjector):
        """Provide the object instance given a config and injector."""
        instance_cls = self._instance_cls
        if isinstance(instance_cls, str):
            instance_cls = ClassLoader.load_class(instance_cls)
            self._instance_cls = instance_cls
        args = []
        for arg in self._ctor_args:
            if isinstance(arg, self.Inject):
                arg = injector.inject(arg.base_class)
            args.append(arg)
        kwargs = {}
        for arg_name, arg in self._ctor_kwargs.items():
            if isinstance(arg, self.Inject):
                arg = injector.inject(arg.base_class)
            kwargs[arg_name] = arg
        instance = instance_cls(*args, **kwargs)
        if self._init_method:
            getattr(instance, self._init_method)()
        return instance


class CachedProvider(BaseProvider):
    """Cache the result of another provider."""

    def __init__(self, provider: BaseProvider):
        """Initialize the cached provider instance."""
        if not provider:
            raise ValueError("Cache provider input must not be empty.")
        self._instance = None
        self._provider = provider

    def provide(self, config: BaseSettings, injector: BaseInjector):
        """Provide the object instance given a config and injector."""
        if not self._instance:
            self._instance = self._provider.provide(config, injector)
        return self._instance


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
            collector: Collector = injector.inject(Collector, required=False)
            if collector:
                collector.wrap(
                    instance, self._methods, ignore_missing=self._ignore_missing
                )
        return instance
