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
        id: Optional[str] = None,
        is_production: bool = True,
        is_write: bool = False,
        keepalive: int = 5,
        read_only: bool = False,
        socks_proxy: Optional[str] = None,
        pool_name: Optional[str] = None,
        endorser_alias: Optional[str] = None,
        endorser_did: Optional[str] = None,
    ):
        """Initialize LedgerConfigInstance."""
        self.id = id or str(uuid4())
        self.is_production = is_production
        self.is_write = is_write
        self.keepalive = keepalive
        self.read_only = read_only
        self.socks_proxy = socks_proxy
        self.pool_name = pool_name or self.id
        self.endorser_alias = endorser_alias
        self.endorser_did = endorser_did


class LedgerConfigInstanceSchema(BaseModelSchema):
    """Single LedgerConfigInstance Schema."""

    class Meta:
        """LedgerConfigInstanceSchema metadata."""

        model_class = LedgerConfigInstance
        unknown = EXCLUDE

    id = fields.Str(
        required=True,
        metadata={
            "description": "Ledger identifier. Auto-generated UUID4 if not provided",
            "example": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        },
    )
    is_production = fields.Bool(
        required=True, metadata={"description": "Production-grade ledger (true/false)"}
    )
    is_write = fields.Bool(
        required=False,
        metadata={"description": "Write capability enabled (default: False)"},
    )
    keepalive = fields.Int(
        required=False,
        metadata={
            "description": "Keep-alive timeout in seconds for idle connections",
            "default": 5,
        },
    )
    read_only = fields.Bool(
        required=False, metadata={"description": "Read-only access (default: False)"}
    )
    socks_proxy = fields.Str(
        required=False, metadata={"description": "SOCKS proxy URL (optional)"}
    )
    pool_name = fields.Str(
        required=False,
        metadata={
            "description": "Ledger pool name (defaults to ledger ID if not specified)",
            "example": "bcovrin-test-pool",
        },
    )
    endorser_alias = fields.Str(
        required=False, metadata={"description": "Endorser service alias (optional)"}
    )
    endorser_did = fields.Str(
        required=False, metadata={"description": "Endorser DID (optional)"}
    )

    @pre_load
    def validate_id(self, data, **kwargs):
        """Check if id is present, if not then set to UUID4."""
        if "id" not in data:
            data["id"] = str(uuid4())
        return data

    @pre_load
    def set_defaults(self, data, **kwargs):
        """Set default values for optional fields."""
        data.setdefault("is_write", False)
        data.setdefault("keepalive", 5)
        data.setdefault("read_only", False)
        return data


class LedgerConfigListSchema(OpenAPISchema):
    """Schema for Ledger Config List."""

    production_ledgers = fields.List(  # Changed from ledger_config_list
        fields.Nested(LedgerConfigInstanceSchema(), required=True),
        required=True,
        metadata={"description": "Production ledgers (may be empty)"},
    )
    non_production_ledgers = fields.List(  # Added new field
        fields.Nested(LedgerConfigInstanceSchema(), required=True),
        required=True,
        metadata={"description": "Non-production ledgers (may be empty)"},
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
