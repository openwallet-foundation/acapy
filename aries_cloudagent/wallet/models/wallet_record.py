"""Wallet record"""

from typing import Any

from aries_cloudagent.config.injection_context import InjectionContext
from marshmallow import fields

from ...messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from ...messaging.valid import UUIDFour
from ..base import BaseWallet
from ..error import WalletNotFoundError


class WalletRecord(BaseExchangeRecord):
    """Represents a wallet record."""

    class Meta:
        """WalletRecord metadata."""

        schema_class = "WalletRecordSchema"

    RECORD_TYPE = "wallet_record"
    RECORD_ID_NAME = "wallet_id"
    TAG_NAMES = {"name", "label", "image_url"}

    def __init__(
        self,
        *,
        wallet_id: str = None,
        name: str,
        config: dict,
        label: str = "",
        image_url: str = "",
        webhook_urls: list = [],
        trace: bool = False,
        **kwargs,
    ):
        """Initialize a new WalletRecord."""
        super().__init__(wallet_id, trace=trace, **kwargs)
        self._id = wallet_id
        self.name = name
        self.config = config
        self.label = label
        self.image_url = image_url
        self.webhook_urls = webhook_urls
        self.trace = trace

    def get_config_as_settings(self):
        # Wallet settings need to be prefixed with `wallet.`
        return {f"wallet.{k}": v for k, v in self.config.items()}

    async def get_instance(self, context):
        wallet_instance: BaseWallet = await context.inject(
            BaseWallet, settings=self.get_config_as_settings(),
        )
        return wallet_instance

    @property
    def wallet_id(self) -> str:
        """Accessor for the ID associated with this record."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this record."""
        return {prop: getattr(self, prop) for prop in (
            "name", "config", "label", "image_url", "webhook_urls",
        )}

    @property
    def key(self) -> str:
        return self.config.get("key")

    @property
    def type(self) -> str:
        return self.config.get("type")

    @classmethod
    async def retrieve_by_name(
        cls,
        context: InjectionContext,
        name: str,
    ) -> "WalletRecord":
        """Retrieve a wallet record by wallet_name."""
        return await cls.retrieve_by_tag_filter(context, {"name": name})

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

    wallet_id = fields.Str(description="Wallet identifier", example=UUIDFour.EXAMPLE,)
    name = fields.Str(description="Wallet name", example='faber',)
    key = fields.Str(description="Master key used for key derivation", example='faber.key.123',)
    type = fields.Str(description="Type of wallet [basic | indy]", example='indy',)
    label = fields.Str(rdescription="Optional label when connection is established", example='faber',)
    image_url = fields.Str(rdescription="Optional image URL for connection invitation",
                           example="http://image_url/logo.jpg",)
    webhook_urls = fields.List(
        fields.Str(description="Optional webhook URL to receive webhook messages",
                   example="http://localhost:8022/webhooks",))
