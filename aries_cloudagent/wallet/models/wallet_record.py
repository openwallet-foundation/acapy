"""Wallet record"""

from typing import Any

from marshmallow import fields

from ...messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from ...messaging.valid import UUIDFour
from ..base import BaseWallet
from ..error import WalletDuplicateError, WalletNotFoundError


class WalletRecord(BaseExchangeRecord):
    """Represents a wallet record."""

    class Meta:
        """WalletRecord metadata."""

        schema_class = "WalletRecordSchema"

    RECORD_TYPE = "wallet_record"
    RECORD_ID_NAME = "wallet_record_id"

    def __init__(
        self,
        *,
        wallet_record_id: str = None,
        wallet_config: dict = None,
        wallet_name: str = None,
        trace: bool = False,
        **kwargs,
    ):
        """Initialize a new WalletRecord."""
        super().__init__(wallet_record_id, trace=trace, **kwargs)
        self._id = wallet_record_id
        self.wallet_config = wallet_config
        self.trace = trace
        self.wallet_name = wallet_name
        self._associated_keys = []
        self._associated_connections = []

    def get_config_as_settings(self):
        # Wallet settings need to be prefixed with `wallet.`
        return {f"wallet.{k}": v for k, v in self.wallet_config.items()}

    async def get_instance(self, context):
        wallet_instance: BaseWallet = await context.inject(
            BaseWallet, settings=self.get_config_as_settings(),
        )
        return wallet_instance

    def add_key(self, key: str):
        """Add new associated key to wallet."""
        self._associated_keys.append(key)

    def add_connection(self, connection_id: str):
        """Add new associated connection to wallet."""
        self._associated_connections.append(connection_id)

    @property
    def wallet_record_id(self) -> str:
        """Accessor for the ID associated with this record."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this record."""
        return {prop: getattr(self, prop) for prop in ("wallet_config", "trace", "wallet_name")}

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)

    async def find_for_associated(self, context, associated_type, associated_value) -> []:
        records = await self.query(context)
        matched_records = [
            record for record in records if associated_value in record[associated_type]]
        if len(matched_records) <= 0:
            raise WalletNotFoundError()
            
        return matched_records


class WalletRecordSchema(BaseExchangeSchema):
    """Schema to allow serialization/deserialization of record."""

    class Meta:
        """WalletRecordSchema metadata."""

        model_class = WalletRecord

    wallet_record_id = fields.Str(
        required=True, description="Wallet record ID", example=UUIDFour.EXAMPLE,
    )
    wallet_config = fields.Dict(required=True, description="Wallet config")
