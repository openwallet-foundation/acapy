"""Issuer credential revocation information."""

import json
from collections.abc import Sequence
from typing import List, Optional

from marshmallow import fields

from ...core.profile import ProfileSession
from ...messaging.models.base_record import BaseRecordSchema
from ...messaging.valid import UUID4_EXAMPLE
from ...revocation.models.issuer_cred_rev_record import (
    IssuerCredRevRecord as IndyIssuerCredRevRecord,
)
from ...storage.base import BaseStorage


class IssuerCredRevRecord(IndyIssuerCredRevRecord):
    """Represents credential revocation information to retain post-issue."""

    class Meta:
        """IssuerCredRevRecord metadata."""

        schema_class = "IssuerCredRevRecordSchemaAnonCreds"

    @classmethod
    async def retrieve_by_ids(
        cls,
        session: ProfileSession,
        rev_reg_id: str,
        cred_rev_id: str | List[str],
        *,
        for_update: bool = False,
    ) -> Sequence["IssuerCredRevRecord"]:
        """Retrieve a list of issuer cred rev records by rev reg id and cred rev ids."""
        cred_rev_ids = [cred_rev_id] if isinstance(cred_rev_id, str) else cred_rev_id

        tag_query = {
            "rev_reg_id": rev_reg_id,
            "cred_rev_id": {"$in": cred_rev_ids},
        }

        storage = session.inject(BaseStorage)
        storage_records = await storage.find_all_records(
            cls.RECORD_TYPE,
            tag_query,
            options={
                "for_update": for_update,
            },
        )

        rev_reg_records = [
            cls.from_storage(record.id, json.loads(record.value))
            for record in storage_records
        ]

        return rev_reg_records

    # Override query_by_ids to return the correct type
    @classmethod
    async def query_by_ids(
        cls,
        session: ProfileSession,
        *,
        cred_def_id: Optional[str] = None,
        rev_reg_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Sequence["IssuerCredRevRecord"]:
        """Retrieve issuer cred rev records by cred def id and/or rev reg id.

        Args:
            session: the profile session to use
            cred_def_id: the cred def id by which to filter
            rev_reg_id: the rev reg id by which to filter
            state: a state value by which to filter

        """
        # Call parent method but cast return type
        return await super().query_by_ids(
            session,
            cred_def_id=cred_def_id,
            rev_reg_id=rev_reg_id,
            state=state,
        )


class IssuerCredRevRecordSchemaAnonCreds(BaseRecordSchema):
    """Schema to allow de/serialization of credential revocation records."""

    class Meta:
        """IssuerCredRevRecordSchemaAnonCreds metadata."""

        model_class = IssuerCredRevRecord

    record_id = fields.Str(
        required=False,
        metadata={
            "description": "Issuer credential revocation record identifier",
            "example": UUID4_EXAMPLE,
        },
    )
    state = fields.Str(
        required=False,
        metadata={
            "description": "Issue credential revocation record state",
            "example": IssuerCredRevRecord.STATE_ISSUED,
        },
    )
    cred_ex_id = fields.Str(
        required=False,
        metadata={
            "description": "Credential exchange record identifier at credential issue",
            "example": UUID4_EXAMPLE,
        },
    )
    rev_reg_id = fields.Str(
        required=False,
        metadata={"description": "Revocation registry identifier"},
    )
    cred_def_id = fields.Str(
        required=False,
        metadata={"description": "Credential definition identifier"},
    )
    cred_rev_id = fields.Str(
        required=False,
        metadata={"description": "Credential revocation identifier"},
    )
    cred_ex_version = fields.Str(
        required=False, metadata={"description": "Credential exchange version"}
    )
