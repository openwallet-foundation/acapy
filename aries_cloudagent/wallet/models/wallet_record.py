"""Wallet record."""

from typing import Any, Optional

from marshmallow import fields
from marshmallow import validate
from marshmallow.utils import EXCLUDE

from ...messaging.models.base_record import (
    BaseRecord,
    BaseRecordSchema,
)
from ...messaging.valid import UUIDFour
from ..base import BaseWallet


class WalletRecord(BaseRecord):
    """Represents a wallet record."""

    class Meta:
        """WalletRecord metadata."""

        schema_class = "WalletRecordSchema"

    RECORD_TYPE = "wallet_record"
    RECORD_ID_NAME = "wallet_record_id"

    TAG_NAMES = {"wallet_name"}

    MODE_MANAGED = "managed"
    MODE_UNMANAGED = "unmanaged"

    def __init__(
        self,
        *,
        wallet_record_id: str = None,
        wallet_config: dict = None,
        key_management_mode: str = None,
        # MTODO: how to make this a tag without making it
        # a constructor param
        wallet_name: str = None,
        **kwargs,
    ):
        """Initialize a new WalletRecord."""
        super().__init__(wallet_record_id, **kwargs)
        self._id = wallet_record_id
        self.wallet_config = wallet_config
        self.key_management_mode = key_management_mode

    def get_config_as_settings(self):
        """Get the wallet config as settings dict."""
        config = {**self.wallet_config, "id": self.wallet_record_id}
        # Wallet settings need to be prefixed with `wallet.`
        return {f"wallet.{k}": v for k, v in config.items()}

    async def get_instance(self, context, extra_settings={}):
        """Get instance of wallet using wallet config."""
        wallet_instance: BaseWallet = await context.inject(
            BaseWallet,
            settings={**self.get_config_as_settings(), **extra_settings},
        )
        return wallet_instance

    @property
    def wallet_record_id(self) -> str:
        """Accessor for the ID associated with this record."""
        return self._id

    @property
    def wallet_name(self) -> Optional[str]:
        """Accessor for the name of the wallet."""
        return self.wallet_config.get("name")

    @property
    def wallet_type(self) -> str:
        """Accessor for the type of the wallet."""
        return self.wallet_config.get("type")

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this record."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "wallet_config",
                "key_management_mode",
            )
        }

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class WalletRecordSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of record."""

    class Meta:
        """WalletRecordSchema metadata."""

        model_class = WalletRecord
        unknown = EXCLUDE

    wallet_record_id = fields.Str(
        required=True,
        description="Wallet record ID",
        example=UUIDFour.EXAMPLE,
    )
    wallet_config = fields.Dict(required=True, description="Wallet config")
    key_management_mode = fields.Str(
        required=True,
        description="Mode regarding management of wallet key",
        validate=validate.OneOf(
            [
                WalletRecord.MODE_MANAGED,
                WalletRecord.MODE_UNMANAGED,
            ]
        ),
    )
