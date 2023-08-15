"""Manage Indy-SDK profile interaction."""

import asyncio
import logging
from typing import Any, Mapping
import warnings
from weakref import finalize, ref

from ...cache.base import BaseCache
from ...config.injection_context import InjectionContext
from ...config.provider import ClassProvider
from ...core.error import ProfileError
from ...core.profile import Profile, ProfileManager, ProfileSession
from ...ledger.base import BaseLedger
from ...ledger.indy import IndySdkLedger, IndySdkLedgerPool
from ...storage.base import BaseStorage, BaseStorageSearch
from ...storage.vc_holder.base import VCHolder
from ...utils.multi_ledger import get_write_ledger_config_for_profile
from ...wallet.base import BaseWallet
from ...wallet.indy import IndySdkWallet
from ..holder import IndyHolder
from ..issuer import IndyIssuer
from ..verifier import IndyVerifier
from .wallet_setup import IndyOpenWallet, IndyWalletConfig

LOGGER = logging.getLogger(__name__)


class IndySdkProfile(Profile):
    """Provide access to Indy profile interaction methods."""

    BACKEND_NAME = "indy"

    def __init__(
        self,
        opened: IndyOpenWallet,
        context: InjectionContext = None,
    ):
        """Create a new IndyProfile instance."""
        super().__init__(context=context, name=opened.name, created=opened.created)
        self.opened = opened
        self.ledger_pool: IndySdkLedgerPool = None
        self.init_ledger_pool()
        self.bind_providers()
        self._finalizer = self._make_finalizer(opened)

    @property
    def name(self) -> str:
        """Accessor for the profile name."""
        return self.opened.name

    @property
    def wallet(self) -> IndyOpenWallet:
        """Accessor for the opened wallet instance."""
        return self.opened

    def init_ledger_pool(self):
        """Initialize the ledger pool."""
        if self.settings.get("ledger.disabled"):
            LOGGER.info("Ledger support is disabled")
            return

        if self.settings.get("ledger.genesis_transactions"):
            self.ledger_pool = self.context.inject(IndySdkLedgerPool, self.settings)

    def bind_providers(self):
        """Initialize the profile-level instance providers."""
        injector = self._context.injector

        injector.bind_provider(
            BaseStorageSearch,
            ClassProvider("aries_cloudagent.storage.indy.IndySdkStorage", self.opened),
        )

        injector.bind_provider(
            IndyHolder,
            ClassProvider(
                "aries_cloudagent.indy.sdk.holder.IndySdkHolder", self.opened
            ),
        )
        injector.bind_provider(
            IndyIssuer,
            ClassProvider("aries_cloudagent.indy.sdk.issuer.IndySdkIssuer", ref(self)),
        )

        injector.bind_provider(
            VCHolder,
            ClassProvider(
                "aries_cloudagent.storage.vc_holder.indy.IndySdkVCHolder", self.opened
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
                    IndySdkLedger,
                    IndySdkLedgerPool(
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
                BaseLedger, ClassProvider(IndySdkLedger, self.ledger_pool, ref(self))
            )
        if self.ledger_pool or self.settings.get("ledger.ledger_config_list"):
            injector.bind_provider(
                IndyVerifier,
                ClassProvider(
                    "aries_cloudagent.indy.sdk.verifier.IndySdkVerifier",
                    ref(self),
                ),
            )

    def session(self, context: InjectionContext = None) -> "ProfileSession":
        """Start a new interactive session with no transaction support requested."""
        return IndySdkProfileSession(self, context=context)

    def transaction(self, context: InjectionContext = None) -> "ProfileSession":
        """
        Start a new interactive session with commit and rollback support.

        If the current backend does not support transactions, then commit
        and rollback operations of the session will not have any effect.
        """
        return IndySdkProfileSession(self, context=context)

    async def close(self):
        """Close the profile instance."""
        if self.opened:
            await self.opened.close()
            self.opened = None

    def _make_finalizer(self, opened: IndyOpenWallet) -> finalize:
        """Return a finalizer for this profile.

        See docs for weakref.finalize for more details on behavior of finalizers.
        """

        async def _closer(opened: IndyOpenWallet):
            try:
                await opened.close()
            except Exception:
                LOGGER.exception("Failed to close wallet from finalizer")

        def _finalize(opened: IndyOpenWallet):
            LOGGER.debug("Profile finalizer called; closing wallet")
            asyncio.get_event_loop().create_task(_closer(opened))

        return finalize(self, _finalize, opened)

    async def remove(self):
        """Remove the profile associated with this instance."""
        if not self.opened:
            raise ProfileError("Wallet must be opened to remove profile")

        self.opened.config.auto_remove = True
        await self.close()


class IndySdkProfileSession(ProfileSession):
    """An active connection to the profile management backend."""

    def __init__(
        self,
        profile: Profile,
        *,
        context: InjectionContext = None,
        settings: Mapping[str, Any] = None
    ):
        """Create a new IndySdkProfileSession instance."""
        super().__init__(profile=profile, context=context, settings=settings)

    async def _setup(self):
        """Create the session or transaction connection, if needed."""
        injector = self._context.injector
        injector.bind_provider(
            BaseWallet, ClassProvider(IndySdkWallet, self.profile.opened)
        )
        injector.bind_provider(
            BaseStorage,
            ClassProvider(
                "aries_cloudagent.storage.indy.IndySdkStorage", self.profile.opened
            ),
        )


class IndySdkProfileManager(ProfileManager):
    """Manager for Indy-SDK wallets."""

    async def provision(
        self, context: InjectionContext, config: Mapping[str, Any] = None
    ) -> Profile:
        """Provision a new instance of a profile."""
        indy_config = IndyWalletConfig(config)
        opened = await indy_config.create_wallet()
        return IndySdkProfile(opened, context)

    async def open(
        self, context: InjectionContext, config: Mapping[str, Any] = None
    ) -> Profile:
        """Open an instance of an existing profile."""
        warnings.warn(
            "Indy wallet type is deprecated, use Askar instead; see: "
            "https://aca-py.org/main/deploying/IndySDKtoAskarMigration/",
            DeprecationWarning,
        )
        LOGGER.warning(
            "Indy wallet type is deprecated, use Askar instead; see: "
            "https://aca-py.org/main/deploying/IndySDKtoAskarMigration/",
        )

        indy_config = IndyWalletConfig(config)
        opened = await indy_config.open_wallet()
        return IndySdkProfile(opened, context)
