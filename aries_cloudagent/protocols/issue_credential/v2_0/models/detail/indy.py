"""Indy-specific credential exchange information with non-secrets storage."""

from typing import Any, Mapping, Sequence

from marshmallow import EXCLUDE, fields

from ......core.profile import ProfileSession
from ......messaging.models.base_record import BaseRecord, BaseRecordSchema
from ......messaging.valid import (
    INDY_CRED_REV_ID_EXAMPLE,
    INDY_CRED_REV_ID_VALIDATE,
    INDY_REV_REG_ID_EXAMPLE,
    INDY_REV_REG_ID_VALIDATE,
    UUID4_EXAMPLE,
)
from .. import UNENCRYPTED_TAGS


class V20CredExRecordIndy(BaseRecord):
    """Credential exchange indy detail record."""

    class Meta:
        """V20CredExRecordIndy metadata."""

        schema_class = "V20CredExRecordIndySchema"

    RECORD_ID_NAME = "cred_ex_indy_id"
    RECORD_TYPE = "indy_cred_ex_v20"
    TAG_NAMES = {"~cred_ex_id"} if UNENCRYPTED_TAGS else {"cred_ex_id"}
    RECORD_TOPIC = "issue_credential_v2_0_indy"

    def __init__(
        self,
        cred_ex_indy_id: str = None,
        *,
        cred_ex_id: str = None,
        cred_id_stored: str = None,
        cred_request_metadata: Mapping = None,
        rev_reg_id: str = None,
        cred_rev_id: str = None,
        **kwargs,
    ):
        """Initialize indy credential exchange record details."""
        super().__init__(cred_ex_indy_id, **kwargs)

        self.cred_ex_id = cred_ex_id
        self.cred_id_stored = cred_id_stored
        self.cred_request_metadata = cred_request_metadata
        self.rev_reg_id = rev_reg_id
        self.cred_rev_id = cred_rev_id

    @property
    def cred_ex_indy_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this credential exchange."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "cred_id_stored",
                "cred_request_metadata",
                "rev_reg_id",
                "cred_rev_id",
            )
        }

    @classmethod
    async def query_by_cred_ex_id(
        cls,
        session: ProfileSession,
        cred_ex_id: str,
    ) -> Sequence["V20CredExRecordIndy"]:
        """Retrieve credential exchange indy detail record(s) by its cred ex id."""
        return await cls.query(
            session=session,
            tag_filter={"cred_ex_id": cred_ex_id},
        )

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class V20CredExRecordIndySchema(BaseRecordSchema):
    """Credential exchange indy detail record detail schema."""

    class Meta:
        """Credential exchange indy detail record schema metadata."""

        model_class = V20CredExRecordIndy
        unknown = EXCLUDE

    cred_ex_indy_id = fields.Str(
        required=False,
        metadata={"description": "Record identifier", "example": UUID4_EXAMPLE},
    )
    cred_ex_id = fields.Str(
        required=False,
        metadata={
            "description": "Corresponding v2.0 credential exchange record identifier",
            "example": UUID4_EXAMPLE,
        },
    )
    cred_id_stored = fields.Str(
        required=False,
        metadata={
            "description": "Credential identifier stored in wallet",
            "example": UUID4_EXAMPLE,
        },
    )
    cred_request_metadata = fields.Dict(
        required=False,
        metadata={"description": "Credential request metadata for indy holder"},
    )
    rev_reg_id = fields.Str(
        required=False,
        validate=INDY_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation registry identifier",
            "example": INDY_REV_REG_ID_EXAMPLE,
        },
    )
    cred_rev_id = fields.Str(
        required=False,
        validate=INDY_CRED_REV_ID_VALIDATE,
        metadata={
            "description": (
                "Credential revocation identifier within revocation registry"
            ),
            "example": INDY_CRED_REV_ID_EXAMPLE,
        },
    )
