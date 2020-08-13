"""Wallet record"""

from typing import Any

from marshmallow import fields

from ...messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from ...messaging.valid import UUIDFour
from ..base import BaseWallet


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
        trace: bool = False,
        **kwargs,
    ):
        """Initialize a new WalletRecord."""
        super().__init__(wallet_record_id, trace=trace, **kwargs)
        self._id = wallet_record_id
        self.wallet_config = wallet_config
        self.trace = trace

    def get_config_as_settings(self):
        # Wallet settings need to be prefixed with `wallet.`
        return {f"wallet.{k}": v for k, v in self.wallet_config.items()}

    async def get_instance(self, context):
        wallet_instance: BaseWallet = await context.inject(
            BaseWallet, settings=self.get_config_as_settings(),
        )
        return wallet_instance

    @property
    def wallet_record_id(self) -> str:
        """Accessor for the ID associated with this record."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this record."""
        return {prop: getattr(self, prop) for prop in ("wallet_config", "trace",)}

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class WalletRecordSchema(BaseExchangeSchema):
    """Schema to allow serialization/deserialization of record."""

    class Meta:
        """WalletRecordSchema metadata."""

        model_class = WalletRecord

    wallet_record_id = fields.Str(
        required=True, description="Wallet record ID", example=UUIDFour.EXAMPLE,
    )
    wallet_config = fields.Dict(required=True, description="Wallet config")
