"""Manage Aries-Askar profile interaction."""

import asyncio
import logging
import time
from typing import Any, Mapping, Optional
from weakref import ref

from aries_askar import AskarError, Session
from aries_askar import Store as AskarStore

from ..cache.base import BaseCache
from ..config.injection_context import InjectionContext
from ..config.provider import ClassProvider
from ..core.error import ProfileError
from ..core.profile import Profile, ProfileManager, ProfileSession
from ..database_manager.db_errors import DBError
from ..database_manager.dbstore import DBStore, DBStoreError, DBStoreSession
from ..indy.holder import IndyHolder
from ..indy.issuer import IndyIssuer
from ..ledger.base import BaseLedger
from ..ledger.indy_vdr import IndyVdrLedger, IndyVdrLedgerPool
from ..storage.base import BaseStorage, BaseStorageSearch
from ..storage.vc_holder.base import VCHolder
from ..utils.multi_ledger import get_write_ledger_config_for_profile
from ..wallet.base import BaseWallet
from ..wallet.crypto import validate_seed
from .store_kanon import KanonOpenStore, KanonStoreConfig

LOGGER = logging.getLogger(__name__)


class KanonAnonCredsProfile(Profile):
    """Kanon AnonCreds profile implementation."""

    BACKEND_NAME = "kanon-anoncreds"
    TEST_PROFILE_NAME = "test-profile"

    def __init__(
        self,
        opened: KanonOpenStore,
        context: Optional[InjectionContext] = None,
        *,
        profile_id: Optional[str] = None,
    ):
        """Initialize the KanonAnonCredsProfile with a store and context."""
        super().__init__(
            context=context, name=profile_id or opened.name, created=opened.created
        )
        self.opened = opened  # Store the single KanonOpenStore instance
        self.ledger_pool: Optional[IndyVdrLedgerPool] = None
        self.profile_id = profile_id
        self.init_ledger_pool()
        self.bind_providers()

    @property
    def name(self) -> str:
        """Accessor for the profile name."""
        return self.profile_id or self.opened.name

    @property
    def store(self) -> DBStore:
        """Accessor for the opened Store instance."""
        return self.opened.db_store

    async def remove(self):
        """Remove profile."""
        if not self.profile_id:
            return  # Nothing to remove

        errors = []
        # Attempt to remove from DBStore
        try:
            await self.opened.db_store.remove_profile(self.profile_id)
        except (DBStoreError, Exception) as e:
            errors.append(f"Failed to remove profile from DBStore: {str(e)}")

        # Attempt to remove from Askar
        try:
            await self.opened.askar_store.remove_profile(self.profile_id)
        except (AskarError, Exception) as e:
            errors.append(f"Failed to remove profile from Askar: {str(e)}")

        # If any errors occurred, raise an exception
        if errors:
            raise ProfileError(
                "Errors occurred while removing profile: " + "; ".join(errors)
            )

    def init_ledger_pool(self):
        """Initialize the ledger pool."""
        if self.settings.get("ledger.disabled"):
            LOGGER.info("Ledger support is disabled")
            return
        if self.settings.get("ledger.genesis_transactions"):
            pool_name = self.settings.get("ledger.pool_name", "default")
            keepalive = int(self.settings.get("ledger.keepalive", 5))
            read_only = bool(self.settings.get("ledger.read_only", False))
            socks_proxy = self.settings.get("ledger.socks_proxy")
            if read_only:
                LOGGER.warning("Note: setting ledger to read-only mode")
            genesis_transactions = self.settings.get("ledger.genesis_transactions")
            cache = self.context.injector.inject_or(BaseCache)
            self.ledger_pool = IndyVdrLedgerPool(
                pool_name,
                keepalive=keepalive,
                cache=cache,
                genesis_transactions=genesis_transactions,
                read_only=read_only,
                socks_proxy=socks_proxy,
            )

    def bind_providers(self):
        """Initialize the profile-level instance providers."""
        injector = self._context.injector

        injector.bind_provider(
            BaseStorageSearch,
            ClassProvider(
                "acapy_agent.storage.kanon_storage.KanonStorageSearch", ref(self)
            ),
        )
        injector.bind_provider(
            VCHolder,
            ClassProvider(
                "acapy_agent.storage.vc_holder.kanon.KanonVCHolder",
                ref(self),
            ),
        )
        injector.bind_provider(
            IndyHolder,
            ClassProvider(
                "acapy_agent.indy.credx.holder_kanon.KanonIndyCredxHolder",
                ref(self),
            ),
        )
        injector.bind_provider(
            IndyIssuer,
            ClassProvider(
                "acapy_agent.indy.credx.issuer_kanon.KanonIndyCredxIssuer", ref(self)
            ),
        )
        if (
            self.settings.get("ledger.ledger_config_list")
            and len(self.settings.get("ledger.ledger_config_list")) >= 1
        ):
            write_ledger_config = get_write_ledger_config_for_profile(
                settings=self.settings
            )
            cache = self.context.injector.inject_or(BaseCache)
            injector.bind_provider(
                BaseLedger,
                ClassProvider(
                    IndyVdrLedger,
                    IndyVdrLedgerPool(
                        write_ledger_config.get("pool_name")
                        or write_ledger_config.get("id"),
                        keepalive=write_ledger_config.get("keepalive"),
                        cache=cache,
                        genesis_transactions=write_ledger_config.get(
                            "genesis_transactions"
                        ),
                        read_only=write_ledger_config.get("read_only"),
                        socks_proxy=write_ledger_config.get("socks_proxy"),
                    ),
                    ref(self),
                ),
            )
            self.settings["ledger.write_ledger"] = write_ledger_config.get("id")
            if (
                "endorser_alias" in write_ledger_config
                and "endorser_did" in write_ledger_config
            ):
                self.settings["endorser.endorser_alias"] = write_ledger_config.get(
                    "endorser_alias"
                )
                self.settings["endorser.endorser_public_did"] = write_ledger_config.get(
                    "endorser_did"
                )
        elif self.ledger_pool:
            injector.bind_provider(
                BaseLedger, ClassProvider(IndyVdrLedger, self.ledger_pool, ref(self))
            )

    def session(self, context: Optional[InjectionContext] = None) -> ProfileSession:
        """Create a new session."""
        return KanonAnonCredsProfileSession(self, False, context=context)

    def transaction(self, context: Optional[InjectionContext] = None) -> ProfileSession:
        """Create a new transaction."""
        return KanonAnonCredsProfileSession(self, True, context=context)

    async def close(self):
        """Close both stores."""
        # ***CHANGE***: Close the single opened store
        if self.opened:
            await self.opened.close()
            self.opened = None


class KanonAnonCredsProfileSession(ProfileSession):
    """An active connection to the profile management backend."""

    def __init__(
        self,
        profile: KanonAnonCredsProfile,
        is_txn: bool,
        *,
        context: Optional[InjectionContext] = None,
        settings: Mapping[str, Any] = None,
    ):
        """Create a new KanonAnonCredsProfileSession instance."""
        super().__init__(profile=profile, context=context, settings=settings)

        if is_txn:
            self._dbstore_opener = profile.opened.db_store.transaction(profile.profile_id)
            self._askar_opener = profile.opened.askar_store.transaction(
                profile.profile_id
            )
        else:
            self._dbstore_opener = profile.opened.db_store.session(profile.profile_id)
            self._askar_opener = profile.opened.askar_store.session(profile.profile_id)

        self._profile = profile
        self._dbstore_handle: Optional[DBStoreSession] = None
        self._askar_handle: Optional[Session] = None
        self._acquire_start: Optional[float] = None
        self._acquire_end: Optional[float] = None

    # THIS IS ONLY USED BY acapy_agent.wallet.anoncreds_upgrade.
    # It needs a handle for dbstore only.
    @property
    def handle(self) -> DBStoreSession:
        """Accessor for the Session instance."""
        return self._dbstore_handle

    @property
    def dbstore_handle(self) -> DBStoreSession:
        """Accessor for DBStore session."""
        return self._dbstore_handle

    @property
    def askar_handle(self) -> Session:
        """Accessor for Askar session."""
        return self._askar_handle

    @property
    def store(self) -> DBStore:
        """Get store instance."""
        return self._profile and self._profile.store

    @property
    def is_transaction(self) -> bool:
        """Check if this is a transaction."""
        if self._dbstore_handle and self._askar_handle:
            return (
                self._dbstore_handle.is_transaction and self._askar_handle.is_transaction
            )
        if self._dbstore_opener and self._askar_opener:
            return (
                self._dbstore_opener.is_transaction and self._askar_opener.is_transaction
            )
        raise ProfileError("Session not open")

    async def _setup(self):
        self._acquire_start = time.perf_counter()
        is_txn = getattr(self._dbstore_opener, "is_transaction", "unknown")
        LOGGER.debug(
            "KanonSession._setup starting for profile=%s, is_txn=%s",
            self._profile.profile_id,
            is_txn,
        )
        try:
            # Open both sessions in parallel for better performance
            LOGGER.debug("Opening DBStore and Askar sessions in parallel...")
            self._dbstore_handle, self._askar_handle = await asyncio.gather(
                asyncio.wait_for(self._dbstore_opener, 60),
                asyncio.wait_for(self._askar_opener, 60),
            )
            LOGGER.debug(
                "Sessions opened successfully in %.3fs",
                time.perf_counter() - self._acquire_start,
            )
        except asyncio.TimeoutError:
            LOGGER.error(
                "TIMEOUT waiting for store session after %.3fs for profile=%s",
                time.perf_counter() - self._acquire_start,
                self._profile.profile_id,
            )
            raise
        except DBError as err:
            LOGGER.error(
                "DBError opening store session after %.3fs: %s",
                time.perf_counter() - self._acquire_start,
                str(err),
            )
            raise ProfileError("Error opening store session") from err
        except Exception as err:
            LOGGER.error(
                "Unexpected error opening store session after %.3fs: %s - %s",
                time.perf_counter() - self._acquire_start,
                type(err).__name__,
                str(err),
            )
            raise

        self._acquire_end = time.perf_counter()
        self._dbstore_opener = None
        self._askar_opener = None

        injector = self._context.injector
        injector.bind_provider(
            BaseWallet,
            ClassProvider("acapy_agent.wallet.kanon_wallet.KanonWallet", ref(self)),
        )
        injector.bind_provider(
            BaseStorage,
            ClassProvider("acapy_agent.storage.kanon_storage.KanonStorage", ref(self)),
        )

    async def _teardown(self, commit: Optional[bool] = None):
        """Close both sessions, committing transactions if needed."""
        teardown_start = time.perf_counter()
        LOGGER.debug(
            "KanonSession._teardown starting, commit=%s, profile=%s",
            commit,
            self._profile.profile_id,
        )
        if commit and self.is_transaction:
            try:
                LOGGER.debug("Committing DBStore transaction...")
                await self._dbstore_handle.commit()
                LOGGER.debug("Committing Askar transaction...")
                await self._askar_handle.commit()
                LOGGER.debug("Both transactions committed")
            except DBError as err:
                LOGGER.error("Error committing transaction: %s", str(err))
                raise ProfileError("Error committing transaction") from err
        if self._dbstore_handle:
            LOGGER.debug("Closing DBStore handle...")
            await self._dbstore_handle.close()
        if self._askar_handle:
            LOGGER.debug("Closing Askar handle...")
            await self._askar_handle.close()
        LOGGER.debug(
            "KanonSession._teardown completed in %.3fs",
            time.perf_counter() - teardown_start,
        )
        self._check_duration()

    def _check_duration(self):
        """Check transaction duration for monitoring purposes."""
        if self._acquire_start and self._acquire_end:
            duration = time.perf_counter() - self._acquire_start
            if duration > 5.0:
                LOGGER.warning(
                    "Long-running session detected: %.3fs for profile=%s",
                    duration,
                    self._profile.profile_id,
                )

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, "_dbstore_handle") and self._dbstore_handle:
            self._check_duration()


class KanonAnonProfileManager(ProfileManager):
    """Manager for Aries-Askar stores."""

    async def provision(
        self, context: InjectionContext, config: Mapping[str, Any] = None
    ) -> Profile:
        """Provision a new profile."""
        print(f"KanonProfileManager Provision store with config: {config}")

        # Provision both stores with a single config
        store_config = KanonStoreConfig(config)  # No store_class specialization needed
        opened = await store_config.open_store(
            provision=True, in_memory=config.get("test")
        )

        return KanonAnonCredsProfile(opened, context)

    async def open(
        self, context: InjectionContext, config: Mapping[str, Any] = None
    ) -> Profile:
        """Open an instance of an existing profile."""
        store_config = KanonStoreConfig(config)  # No store_class specialization needed
        opened = await store_config.open_store(
            provision=False, in_memory=config.get("test")
        )

        # Note: Health checks removed - if opening fails, exceptions are raised
        # by the open_store method. The stores will be validated when first used.

        return KanonAnonCredsProfile(opened, context)

    @classmethod
    async def generate_store_key(cls, seed: Optional[str] = None) -> str:
        """Generate a raw store key."""
        return AskarStore.generate_raw_key(validate_seed(seed))
