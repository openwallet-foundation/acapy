"""Service provider implementations."""

from .base import BaseProvider, BaseSettings, BaseInjector


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

    def __init__(self, instance_cls, *ctor_args, async_init: str = None, **ctor_kwargs):
        """Initialize the class provider."""
        self._async_init = async_init
        self._ctor_args = ctor_args
        self._ctor_kwargs = ctor_kwargs
        self._instance_cls = instance_cls

    async def provide(self, config: BaseSettings, injector: BaseInjector):
        """Provide the object instance given a config and injector."""
        instance = self._instance_cls(*self._ctor_args, **self._ctor_kwargs)
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
