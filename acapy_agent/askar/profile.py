"""Manage Aries-Askar profile interaction."""

import asyncio
import logging
import time
from typing import Any, Mapping, Optional
from weakref import ref

from aries_askar import AskarError, Session, Store

from ..config.injection_context import InjectionContext
from ..config.provider import ClassProvider
from ..core.error import ProfileError
from ..core.profile import Profile, ProfileManager, ProfileSession
from ..resolver.did_resolver import DIDResolver
from ..storage.base import BaseStorage, BaseStorageSearch
from ..storage.vc_holder.base import VCHolder
from ..wallet.base import BaseWallet
from ..wallet.crypto import validate_seed
from .store import AskarOpenStore, AskarStoreConfig

LOGGER = logging.getLogger(__name__)


class AskarProfile(Profile):
    """Provide access to Aries-Askar profile interaction methods."""

    BACKEND_NAME = "askar"

    def __init__(
        self,
        opened: AskarOpenStore,
        context: Optional[InjectionContext] = None,
        *,
        profile_id: Optional[str] = None,
    ):
        """Create a new AskarProfile instance."""
        super().__init__(
            context=context, name=profile_id or opened.name, created=opened.created
        )
        self.opened = opened
        self.profile_id = profile_id
        self.bind_providers()

    @property
    def name(self) -> str:
        """Accessor for the profile name."""
        return self.profile_id or self.opened.name

    @property
    def store(self) -> Store:
        """Accessor for the opened Store instance."""
        return self.opened.store

    async def remove(self):
        """Remove the profile."""
        if self.profile_id:
            await self.store.remove_profile(self.profile_id)

    def bind_providers(self):
        """Initialize the profile-level instance providers."""
        injector = self._context.injector

        if self.context.settings.get("experiment.didcomm_v2"):
            from didcomm_messaging.resolver import DIDResolver as DMPResolver

            injector.bind_provider(
                DMPResolver,
                ClassProvider(
                    "acapy_agent.didcomm_v2.adapters.ResolverAdapter",
                    ref(self),
                    ClassProvider.Inject(DIDResolver),
                ),
            )

        injector.bind_provider(
            BaseStorageSearch,
            ClassProvider("acapy_agent.storage.askar.AskarStorageSearch", ref(self)),
        )
        injector.soft_bind_provider(
            VCHolder,
            ClassProvider(
                "acapy_agent.storage.vc_holder.askar.AskarVCHolder",
                ClassProvider.Inject(Profile),
            ),
        )

    def session(
        self, context: Optional[InjectionContext] = None
    ) -> "AskarProfileSession":
        """Start a new interactive session with no transaction support requested."""
        return AskarProfileSession(self, False, context=context)

    def transaction(
        self, context: Optional[InjectionContext] = None
    ) -> "AskarProfileSession":
        """Start a new interactive session with commit and rollback support.

        If the current backend does not support transactions, then commit
        and rollback operations of the session will not have any effect.
        """
        return AskarProfileSession(self, True, context=context)

    async def close(self):
        """Close the profile instance."""
        if self.opened:
            await self.opened.close()
            self.opened = None


class AskarProfileSession(ProfileSession):
    """An active connection to the profile management backend."""

    def __init__(
        self,
        profile: AskarProfile,
        is_txn: bool,
        *,
        context: Optional[InjectionContext] = None,
        settings: Mapping[str, Any] = None,
    ):
        """Create a new ProfileSession instance."""
        super().__init__(profile=profile, context=context, settings=settings)
        self._profile = profile
        if is_txn:
            self._opener = self._profile.store.transaction(profile.profile_id)
        else:
            self._opener = self._profile.store.session(profile.profile_id)
        self._handle: Optional[Session] = None
        self._acquire_start: Optional[float] = None
        self._acquire_end: Optional[float] = None

    @property
    def handle(self) -> Session:
        """Accessor for the Session instance."""
        return self._handle

    @property
    def store(self) -> Store:
        """Accessor for the Store instance."""
        return self._profile and self._profile.store

    @property
    def is_transaction(self) -> bool:
        """Check if the session supports commit and rollback operations."""
        if self._handle:  # opened
            return self._handle.is_transaction
        if self._opener:  # opening
            return self._opener.is_transaction

        raise ProfileError("Session not open")

    async def _setup(self):
        """Create the session or transaction connection, if needed."""
        self._acquire_start = time.perf_counter()
        try:
            self._handle = await asyncio.wait_for(self._opener, 10)
        except AskarError as err:
            raise ProfileError("Error opening store session") from err
        self._acquire_end = time.perf_counter()
        self._opener = None

        injector = self._context.injector
        injector.bind_provider(
            BaseWallet,
            ClassProvider("acapy_agent.wallet.askar.AskarWallet", ref(self)),
        )
        injector.bind_provider(
            BaseStorage,
            ClassProvider("acapy_agent.storage.askar.AskarStorage", ref(self)),
        )

        if self.profile.settings.get("experiment.didcomm_v2"):
            from didcomm_messaging import (
                CryptoService,
                DIDCommMessaging,
                PackagingService,
                RoutingService,
                SecretsManager,
            )
            from didcomm_messaging.resolver import DIDResolver as DMPResolver

            injector.bind_provider(
                SecretsManager,
                ClassProvider(
                    "acapy_agent.didcomm_v2.adapters.SecretsAdapter", ref(self)
                ),
            )

            injector.bind_provider(
                DIDCommMessaging,
                ClassProvider(
                    DIDCommMessaging,
                    ClassProvider.Inject(CryptoService),
                    ClassProvider.Inject(SecretsManager),
                    ClassProvider.Inject(DMPResolver),
                    ClassProvider.Inject(PackagingService),
                    ClassProvider.Inject(RoutingService),
                ),
            )

    async def _teardown(self, commit: Optional[bool] = None):
        """Dispose of the session or transaction connection."""
        if commit:
            try:
                await self._handle.commit()
            except AskarError as err:
                raise ProfileError("Error committing transaction") from err
        if self._handle:
            await self._handle.close()
        self._handle = None
        self._check_duration()

    def _check_duration(self):
        # LOGGER.error(
        #     "release session after %.2f, acquire took %.2f",
        #     end - self._acquire_end,
        #     self._acquire_end - self._acquire_start,
        # )
        # end = time.perf_counter()
        # if end - self._acquire_end > 1.0:
        #     LOGGER.error("Long session")
        #     traceback.print_stack(limit=5)
        pass

    def __del__(self):
        """Delete magic method."""
        if hasattr(self, "_handle") and self._handle:
            self._check_duration()


class AskarProfileManager(ProfileManager):
    """Manager for Aries-Askar stores."""

    async def provision(
        self, context: InjectionContext, config: Mapping[str, Any] = None
    ) -> Profile:
        """Provision a new instance of a profile."""
        store_config = AskarStoreConfig(config)
        opened = await store_config.open_store(
            provision=True, in_memory=config.get("test")
        )
        return AskarProfile(opened, context)

    async def open(
        self, context: InjectionContext, config: Mapping[str, Any] = None
    ) -> Profile:
        """Open an instance of an existing profile."""
        store_config = AskarStoreConfig(config)
        opened = await store_config.open_store(
            provision=False, in_memory=config.get("test")
        )
        return AskarProfile(opened, context)

    @classmethod
    async def generate_store_key(self, seed: Optional[str] = None) -> str:
        """Generate a raw store key."""
        return Store.generate_raw_key(validate_seed(seed))
