"""Wallet record"""

from typing import Any, Sequence

from marshmallow import fields

from ...config.injection_context import InjectionContext
from ...messaging.models.base_record import BaseRecord, BaseRecordSchema
from ...messaging.valid import UUIDFour


class WalletMappingRecord(BaseRecord):
    """Represents a wallet mapping record."""

    class Meta:
        """WalletMappingRecord metadata."""

        schema_class = "WalletMappingRecordSchema"

    RECORD_TYPE = "wallet_mapping_record"
    RECORD_ID_NAME = "record_id"
    TAG_NAMES = {"wallet_name", "key", "connection_id",}

    def __init__(
        self,
        *,
        record_id: str = None,
        state: str = None,
        wallet_name: str,
        key: str = None,
        connection_id: str = None,
        **kwargs,
    ):
        """Initialize a new WalletRecord."""
        super().__init__(record_id, state, **kwargs)
        self.wallet_name = wallet_name
        self.key = key
        self.connection_id = connection_id

    @property
    def record_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @classmethod
    async def retrieve_by_key(
        cls,
        context: InjectionContext,
        key: str,
    ) -> "WalletMappingRecord":
        """Retrieve a wallet mapping record by key."""
        return await cls.retrieve_by_tag_filter(context, {"key": key})

    @classmethod
    async def retrieve_by_conn_id(
        cls,
        context: InjectionContext,
        connection_id: str,
    ) -> "WalletMappingRecord":
        """Retrieve a wallet mapping record by connection_id."""
        return await cls.retrieve_by_tag_filter(context, {"connection_id": connection_id})

    @classmethod
    async def query_by_wallet_name(
        cls,
        context: InjectionContext,
        wallet_name: str,
    ) -> Sequence["WalletMappingRecord"]:
        """Retrieve wallet mappings record by wallet_name."""
        return await cls.query(context, {"wallet_name": wallet_name})

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class WalletMappingRecordSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of record."""

    class Meta:
        """WalletRecordSchema metadata."""

        model_class = WalletMappingRecord

    wallet_name = fields.Str(description="Wallet name", example='faber',)
    key = fields.Str(description="key identifier to find a wallet", example=UUIDFour.EXAMPLE,)
    connection_id = fields.Str(description="connection identifier to find a wallet", example=UUIDFour.EXAMPLE,)
