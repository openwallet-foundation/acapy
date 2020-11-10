"""Multi wallet handler implementation of BaseWallet interface."""

import json

import indy.anoncreds
import indy.did
import indy.crypto
from indy.error import IndyError, ErrorCode
from base64 import b64decode

from .models.wallet_mapping_record import WalletMappingRecord
from ..storage.base import BaseStorage
from ..ledger.base import BaseLedger
from ..storage.error import StorageNotFoundError
from ..wallet.models.wallet_record import WalletRecord
from ..wallet.plugin import load_postgres_plugin
from ..utils.classloader import ClassLoader
from ..config.provider import DynamicProvider
from ..config.injection_context import InjectionContext

from .error import WalletError, WalletDuplicateError
from .error import KeyNotFoundError, WalletAccessError
from .error import WalletNotFoundError


class WalletHandler():
    """Class to handle multiple wallets."""

    WALLET_CLASSES = {
        "basic": "aries_cloudagent.wallet.basic.BasicWallet",
        "indy": "aries_cloudagent.wallet.indy.IndyWallet",
    }
    DEFAULT_KEY = ""
    DEFAULT_KEY_DERIVIATION = "ARGON2I_MOD"
    DEFAULT_NAME = "default"
    DEFAULT_STORAGE_TYPE = None
    DEFAULT_WALLET_CLASS = "aries_cloudagent.wallet.indy.IndyWallet"
    DEFAULT_STORAGE_CLASS = "aries_cloudagent.storage.indy.IndyStorage"
    DEFAULT_LEDGER_CLASS = "aries_cloudagent.ledger.indy.IndyLedger"
    DEFAULT_AUTO_ADD = True

    KEY_DERIVATION_RAW = "RAW"
    KEY_DERIVATION_ARGON2I_INT = "ARGON2I_INT"
    KEY_DERIVATION_ARGON2I_MOD = "ARGON2I_MOD"

    def __init__(self, context: InjectionContext, provider: DynamicProvider, config: dict = None):
        """Initilaize the handler."""
        self.context = context
        self._auto_create = config.get("auto_create", True)
        self._auto_remove = config.get("auto_remove", False)
        self._freshness_time = config.get("freshness_time", False)
        self._key = config.get("key") or self.DEFAULT_KEY
        self._key_derivation_method = (
            config.get("key_derivation_method") or self.DEFAULT_KEY_DERIVIATION
        )
        self._storage_type = config.get("storage_type") or self.DEFAULT_STORAGE_TYPE
        self._storage_config = config.get("storage_config", None)
        self._storage_creds = config.get("storage_creds", None)
        self._master_secret_id = None
        self._wallet_class = config.get("wallet_class") or self.DEFAULT_WALLET_CLASS
        if self._wallet_class == self.DEFAULT_WALLET_CLASS:
            self.WALLET_TYPE = "indy"
        else:
            raise WalletError("Wallet handler only works with indy wallet.")
        self._auto_add = config.get("auto_add") or self.DEFAULT_AUTO_ADD

        if self._storage_type == "postgres_storage":
            load_postgres_plugin(self._storage_config, self._storage_creds)

        self._provider = provider

    async def get_instances(self):
        """Return list of handled instances."""
        return list(self._provider._instances.keys())

    async def add_instance(self, config: dict):
        """
        Add a new instance to the handler to be used during runtime.

        Args:
            config: Settings for the new instance.
        """

        wallet_type = config.get('type') or 'indy'
        wallet_class = self.WALLET_CLASSES[wallet_type]

        if config["name"] in self._provider._instances.keys():
            raise WalletDuplicateError()

        wallet = ClassLoader.load_class(wallet_class)(config)
        await wallet.open()

        # Store wallet in wallet provider.
        # FIXME: might be possible  to handle cleaner?
        self._provider._instances[wallet.name] = wallet

        # We need to adapt the context, so that the storage
        # provider picks up the correct wallet for fetching the connections.
        # TODO: Maybe there is a nicer way to handle this?
        new_context = self.context.copy()
        new_context.settings.set_value("wallet.id", wallet.name)
        # As each leder instance has a wallet instance as property but a 
        # second ledger_pool with the same name cannot be opened we need
        # Also to set a ledger.pool_name.
        new_context.settings.set_value("ledger.pool_name", wallet.name)
        # Inject storage and ledger to add instances with new wallet
        # to provider
        # FIXME: What  about `holder`, `issuer`, etc?
        storage = await new_context.inject(BaseStorage)
        ledger = await new_context.inject(BaseLedger)

    async def set_instance(self, wallet_name: str, context: InjectionContext):
        """Set a specific wallet to open by the provider."""
        instances = await self.get_instances()
        if wallet_name not in instances:
            # wallet is not opened
            # query wallet and open wallet if exist
            wallet_records = await self.get_wallets({"name": wallet_name})
            if wallet_records:
                wallet_record = wallet_records[0]
                await self.add_instance(wallet_record.config)
            else:
                raise WalletNotFoundError('Requested wallet is not exist in storage.')
        context.settings.set_value("wallet.id", wallet_name)
        context.settings.set_value("ledger.pool_name", wallet_name)

    async def delete_instance(self, wallet_name: str):
        """
        Delete handled instance from handler and storage.

        Args:
            wallet_name: Identifier of the instance to be deleted.
        """

        try:
            wallet = self._provider._instances.pop(wallet_name)
        except KeyError:
            raise WalletNotFoundError(f"Wallet not found: {wallet_name}")

        if wallet.WALLET_TYPE == 'indy':
            # Delete wallet from storage.
            try:
                await wallet.close()
                await indy.wallet.delete_wallet(
                    config=json.dumps(wallet._wallet_config),
                    credentials=json.dumps(wallet._wallet_access),
                )
            except IndyError as x_indy:
                if x_indy.error_code == ErrorCode.WalletNotFoundError:
                    raise WalletNotFoundError(f"Wallet not found: {wallet_name}")
                raise WalletError(str(x_indy))

        # Remove storage in dynamic provider
        storage_provider = self.context.injector._providers[BaseStorage]
        if wallet_name in storage_provider._instances: del storage_provider._instances[wallet_name]

        # Remove ledger in dynamic provider
        ledger_provider = self.context.injector._providers[BaseLedger]
        if wallet_name in ledger_provider._instances: ledger = ledger_provider._instances.pop(wallet_name)
        await ledger.close()

    async def add_wallet(self, config: dict, label: str, image_url: str, webhook_urls: list):
        """
        Add a new wallet

        Args:
            config: Settings for the new instance.
            label: label for the new instance.
            image_url: image_url for the new instance.
            webhook_urls: webhook_urls for the new instance.
        """
        # Pass default values into config
        config["storage_type"] = self._storage_type
        config["storage_config"] = self._storage_config
        config["storage_creds"] = self._storage_creds

        # check wallet name is already exist in wallet_record
        wallet_name = config["name"]
        post_filter = {"name": wallet_name}
        wallet_records = await WalletRecord.query(self.context, post_filter_positive=post_filter)
        if wallet_records:
            raise WalletDuplicateError(f"specified wallet name already exist: {wallet_name}")

        wallet_record = WalletRecord(
            name=wallet_name,
            config=config,
            label=label,
            image_url=image_url,
            webhook_urls=webhook_urls
        )
        await wallet_record.save(self.context)

        # open wallet if not opened
        instances = await self.get_instances()
        if wallet_name not in instances:
            await self.add_instance(config)

        return wallet_record

    async def get_wallets(self, query: dict = None, ):
        """
        Return wallet records

        Args:
            query: query
        """
        return await WalletRecord.query(self.context, post_filter_positive=query)

    async def get_wallet(self, wallet_id: str):
        """
        Return a wallet record

        Args:
            wallet_id: identifier of wallet
        """
        try:
            wallet_record = await WalletRecord.retrieve_by_id(self.context, record_id=wallet_id)
        except StorageNotFoundError:
            return None
        return wallet_record

    async def remove_wallet(
            self,
            wallet_id: str = None,
            wallet_name: str = None,
    ):
        """
        Remove a wallet

        Args:
            wallet_id: Identifier of the instance to be deleted.
            wallet_name: name of the instance to be deleted.
        """
        if wallet_id:
            wallet_record: WalletRecord = await self.get_wallet(wallet_id)
            if not wallet_record:
                raise WalletNotFoundError(f"No record for wallet_id {wallet_id} found.")
        elif wallet_name:
            wallet_records = await self.get_wallets({"name": wallet_name})
            if len(wallet_records) < 1:
                raise WalletNotFoundError(f"No record for wallet {wallet_name} found.")
            elif len(wallet_records) > 1:
                raise WalletNotFoundError(f"Found multiple records for wallet with name {wallet_name}.")
            else:
                wallet_record: WalletRecord = wallet_records[0]
        else:
            raise WalletNotFoundError(f"Wallet id or wallet id must be specified.")

        wallet_name = wallet_record.name

        # can not delete base wallet
        if wallet_name == self.context.settings.get_value("wallet.name"):
            raise WalletAccessError(f"deleting base wallet is not allowed")

        await wallet_record.delete_record(self.context)

        # Remove all mappings of wallet.
        await self.remove_mappings(wallet_name)

        # close wallet if opened
        instances = await self.get_instances()
        if wallet_name in instances:
            await self.delete_instance(wallet_name)

    async def update_wallet(
            self,
            wallet_id: str = None,
            wallet_name: str = None,
            label: str = None,
            image_url: str = None,
            webhook_urls: list = None
    ):
        """
        Remove a wallet

        Args:
            wallet_id: Identifier of the instance to be updated.
            wallet_name: name of the instance to be updated.
            label: label for the new instance.
            image_url: image_url for the new instance.
            webhook_urls: webhook_urls for the new instance.
        """
        if wallet_id:
            wallet_record: WalletRecord = await self.get_wallet(wallet_id)
            if not wallet_record:
                raise WalletNotFoundError(f"No record for wallet_id {wallet_id} found.")
        elif wallet_name:
            wallet_records = await self.get_wallets({"name": wallet_name})
            if len(wallet_records) < 1:
                raise WalletNotFoundError(f"No record for wallet {wallet_name} found.")
            elif len(wallet_records) > 1:
                raise WalletNotFoundError(f"Found multiple records for wallet with name {wallet_name}.")
            else:
                wallet_record: WalletRecord = wallet_records[0]
        else:
            raise WalletNotFoundError(f"Wallet id or wallet id must be specified.")

        if label is not None:
            wallet_record.label = label
        if image_url is not None:
            wallet_record.image_url = image_url
        if webhook_urls is not None:
            wallet_record.webhook_urls = webhook_urls
        await wallet_record.save(self.context)

        return wallet_record

    async def add_mapping(self, wallet_name: str, connection_id: str = None, key: str = None):
        """
        Add a mapping from connection_id or key to wallet.

        Args:
            connection_id: Indentifier of the new connection.
            key: Identifier of the new key.
            wallet_name: Identifier of the wallet the connection belongs to.
        """
        wallet_mapping_record = WalletMappingRecord(connection_id=connection_id, key=key, wallet_name=wallet_name)
        await wallet_mapping_record.save(self.context)

    async def get_wallet_by_conn_id(self, connection_id: str) -> str:
        """
        Return the identifier of the wallet to which the given key belongs.

        Args:
            connection_id: connection identifier for which the wallet shall be returned.

        Raises:
            KeyNotFoundError: if given key does not belong to handled_keys

        """
        try:
            wallet_mapping_record = await WalletMappingRecord.retrieve_by_conn_id(self.context, connection_id)
        except StorageNotFoundError:
            raise KeyNotFoundError()

        return wallet_mapping_record.wallet_name

    async def get_wallet_by_key(self, key: str) -> str:
        """
        Return the identifier of the wallet to which the given key belongs.

        Args:
            key: verkey or connection key for which the wallet shall be returned.

        Raises:
            KeyNotFoundError: if given key does not belong to handled_keys

        """
        try:
            wallet_mapping_record = await WalletMappingRecord.retrieve_by_key(self.context, key)
        except StorageNotFoundError:
            raise KeyNotFoundError()

        return wallet_mapping_record.wallet_name

    async def get_wallet_by_msg(self, body: bytes) -> [str]:
        """
        Parses an inbound message for recipient keys and returns the wallets
        associated to keys.

        Args:
            body: Inbound raw message

        Raises:
            KeyNotFoundError: if given key does not belong to handled_keys
        """
        msg = json.loads(body)
        protected = json.loads(b64decode(msg['protected']))
        recipients = protected['recipients']
        wallet_ids = []
        # Check each recipient public key (in `kid`) if agent handles a wallet
        # associated to that key.
        for recipient in recipients:
            kid = recipient['header']['kid']
            try:
                wallet_id = await self.get_wallet_by_key(kid)
            except KeyNotFoundError:
                wallet_id = None
            wallet_ids.append(wallet_id)

        return wallet_ids

    async def remove_mappings(self, wallet_name: str):
        """
        Remove the wallet mappings.

        Args:
            wallet_name: wallet name.

        """
        wallet_mapping_records = await WalletMappingRecord.query_by_wallet_name(self.context, wallet_name)
        for wallet_mapping_record in wallet_mapping_records:
            await wallet_mapping_record.delete_record(self.context)

    async def get_webhook_urls(self, context: InjectionContext) -> list:
        """
        Return the list of webhook url of the wallet to which the given context.

        Args:
            context: InjectionContext for which the list of webhook url shall be returned.

        Raises:
            WalletNotFoundError: if given wallet does not exist
        """
        wallet_name = context.settings.get_value("wallet.id")
        wallet_records = await self.get_wallets({"name": wallet_name})
        if wallet_records:
            wallet_record: WalletRecord = wallet_records[0]
        else:
            raise WalletNotFoundError(f"No record for wallet {wallet_name} found.")

        return wallet_record.webhook_urls

    async def get_label(self, context: InjectionContext) -> str:
        """
        Return the label of the wallet to which the given context.

        Args:
            context: InjectionContext for which the label shall be returned.

        Raises:
            WalletNotFoundError: if given wallet does not exist

        """
        wallet_name = context.settings.get_value("wallet.id")
        wallet_records = await self.get_wallets({"name": wallet_name})
        if wallet_records:
            wallet_record: WalletRecord = wallet_records[0]
        else:
            raise WalletNotFoundError(f"No record for wallet {wallet_name} found.")

        return wallet_record.label or None

    async def get_image_url(self, context: InjectionContext) -> str:
        """
        Return the image_url of the wallet to which the given context.

        Args:
            context: InjectionContext for which the image_url shall be returned.

        Raises:
            WalletNotFoundError: if given wallet does not exist
        """
        wallet_name = context.settings.get_value("wallet.id")
        wallet_records = await self.get_wallets({"name": wallet_name})
        if wallet_records:
            wallet_record: WalletRecord = wallet_records[0]
        else:
            raise WalletNotFoundError(f"No record for wallet {wallet_name} found.")

        return wallet_record.image_url or None
