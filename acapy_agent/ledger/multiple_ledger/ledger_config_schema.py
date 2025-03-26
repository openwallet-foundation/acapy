"""Schema for configuring multiple ledgers."""

from typing import Optional

from marshmallow import EXCLUDE, fields, pre_load
from uuid_utils import uuid4

from ...messaging.models.base import BaseModel, BaseModelSchema
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
        is_production: bool = True,  # Fixed type (was str)
        is_write: bool = None,
        keepalive: int = 5,
        read_only: bool = False,
        socks_proxy: Optional[str] = None,
        pool_name: str = None,
        endorser_alias: Optional[str] = None,
        endorser_did: Optional[str] = None,
    ):
        """Initialize LedgerConfigInstance."""
        self.id = id
        self.is_production = is_production
        self.is_write = is_write
        self.keepalive = keepalive
        self.read_only = read_only
        self.socks_proxy = socks_proxy
        self.pool_name = pool_name
        self.endorser_alias = endorser_alias
        self.endorser_did = endorser_did


class LedgerConfigInstanceSchema(BaseModelSchema):
    """Single LedgerConfigInstance Schema."""

    class Meta:
        """LedgerConfigInstanceSchema metadata."""

        model_class = LedgerConfigInstance
        unknown = EXCLUDE

    id = fields.Str(required=True, metadata={"description": "ledger_id"})
    is_production = fields.Bool(required=True, metadata={"description": "is_production"})
    is_write = fields.Bool(required=True, metadata={"description": "is_write"})
    keepalive = fields.Int(required=True, metadata={"description": "keepalive"})
    read_only = fields.Bool(required=True, metadata={"description": "read_only"})
    socks_proxy = fields.Str(required=False, metadata={"description": "socks_proxy"})
    pool_name = fields.Str(required=True, metadata={"description": "pool_name"})
    endorser_alias = fields.Str(
        required=False, metadata={"description": "endorser_alias"}
    )
    endorser_alias = fields.Str(required=False, metadata={"description": "endorser_did"})

    @pre_load
    def validate_id(self, data, **kwargs):
        """Check if id is present, if not then set to UUID4."""
        if "id" not in data:
            data["id"] = str(uuid4())
        return data


class LedgerConfigListSchema(OpenAPISchema):
    """Schema for Ledger Config List."""

    production_ledgers = fields.List(  # Changed from ledger_config_list
        fields.Nested(LedgerConfigInstanceSchema(), required=True),
        required=True,
        metadata={"description": "Production ledgers"},
    )
    non_production_ledgers = fields.List(  # Added new field
        fields.Nested(LedgerConfigInstanceSchema(), required=True),
        required=True,
        metadata={"description": "Non-production ledgers"},
    )


class WriteLedgerSchema(OpenAPISchema):
    """Schema for getting ledger_id for the write ledger."""

    ledger_id = fields.Str()


class ConfigurableWriteLedgersSchema(OpenAPISchema):
    """Schema for list of configurable write ledger."""

    write_ledgers = fields.List(
        fields.Str(metadata={"description": "Ledgers identifiers"}),
        metadata={"description": "List of configurable write ledgers identifiers"},
    )


class MultipleLedgerModuleResultSchema(OpenAPISchema):
    """Schema for the multiple ledger modules endpoint."""
