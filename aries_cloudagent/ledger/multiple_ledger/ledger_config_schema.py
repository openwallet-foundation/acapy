"""Schema for configuring multiple ledgers."""
import uuid

from marshmallow import (
    fields,
    pre_load,
    EXCLUDE,
)

from ...messaging.models.base import BaseModelSchema, BaseModel
from ...messaging.models.openapi import OpenAPISchema


class LedgerConfigInstance(BaseModel):
    """describes each LedgerConfigInstance for multiple ledger support."""

    class Meta:
        """LedgerConfigInstance metadata."""

        schema_class = "LedgerConfigInstanceSchema"

    def __init__(
        self,
        *,
        id: str = None,
        is_production: str = True,
        genesis_transactions: str = None,
        genesis_file: str = None,
        genesis_url: str = None,
    ):
        """Initialize LedgerConfigInstance."""
        self.id = id
        self.is_production = is_production
        self.genesis_transactions = genesis_transactions
        self.genesis_file = genesis_file
        self.genesis_url = genesis_url


class LedgerConfigInstanceSchema(BaseModelSchema):
    """Single LedgerConfigInstance Schema."""

    class Meta:
        """LedgerConfigInstanceSchema metadata."""

        model_class = LedgerConfigInstance
        unknown = EXCLUDE

    id = fields.Str(
        description="ledger_id",
        required=False,
    )
    is_production = fields.Bool(description="is_production", required=False)
    genesis_transactions = fields.Str(
        description="genesis_transactions", required=False
    )
    genesis_file = fields.Str(description="genesis_file", required=False)
    genesis_url = fields.Str(description="genesis_url", required=False)

    @pre_load
    def validate_id(self, data, **kwargs):
        """Check if id is present, if not then set to UUID4."""
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        return data


class LedgerConfigListSchema(OpenAPISchema):
    """Schema for Ledger Config List."""

    ledger_config_list = fields.List(
        fields.Nested(
            LedgerConfigInstanceSchema(),
            required=True,
        ),
        required=True,
    )


class WriteLedgerRequestSchema(OpenAPISchema):
    """Schema for setting/getting ledger_id for the write ledger."""

    ledger_id = fields.Str()


class MultipleLedgerModuleResultSchema(OpenAPISchema):
    """Schema for the multiple ledger modules endpoint."""
