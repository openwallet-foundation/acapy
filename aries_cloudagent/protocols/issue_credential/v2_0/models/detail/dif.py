"""DIF-specific credential exchange information with non-secrets storage."""

from typing import Any

from marshmallow import EXCLUDE, fields

from ......core.profile import ProfileSession
from ......messaging.models.base_record import BaseRecord, BaseRecordSchema
from ......messaging.valid import UUIDFour

from .. import UNENCRYPTED_TAGS


class V20CredExRecordDIF(BaseRecord):
    """Credential exchange DIF detail record."""

    class Meta:
        """V20CredExRecordDIF metadata."""

        schema_class = "V20CredExRecordDIFSchema"

    RECORD_ID_NAME = "cred_ex_dif_id"
    RECORD_TYPE = "dif_cred_ex_v20"
    TAG_NAMES = {"~cred_ex_id"} if UNENCRYPTED_TAGS else {"cred_ex_id"}
    WEBHOOK_TOPIC = "issue_credential_v2_0_dif"

    def __init__(
        self,
        cred_ex_dif_id: str = None,
        *,
        cred_ex_id: str = None,
        # TODO: REMOVE THIS COMMENT AND SET DIF ITEMS BELOW
        item: str = None,
        **kwargs,
    ):
        """Initialize DIF credential exchange record details."""
        super().__init__(cred_ex_dif_id, **kwargs)

        self.cred_ex_id = cred_ex_id
        # TODO: REMOVE THIS COMMENT AND SET DIF ITEMS BELOW
        self.item = item

    @property
    def cred_ex_dif_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this credential exchange."""
        return {
            prop: getattr(self, prop)
            for prop in (
                # TODO: REMOVE THIS COMMENT AND SET DIF ITEMS BELOW
                "item",
            )
        }

    @classmethod
    async def retrieve_by_cred_ex_id(
        cls,
        session: ProfileSession,
        cred_ex_id: str,
    ) -> "V20CredExRecordDIF":
        """Retrieve a credential exchange DIF detail record by its cred ex id."""
        return await cls.retrieve_by_tag_filter(
            session,
            {"cred_ex_id": cred_ex_id},
            None,
        )

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class V20CredExRecordDIFSchema(BaseRecordSchema):
    """Credential exchange DIF detail record detail schema."""

    class Meta:
        """Credential exchange DIF detail record schema metadata."""

        model_class = V20CredExRecordDIF
        unknown = EXCLUDE

    cred_ex_dif_id = fields.Str(
        required=False,
        description="Record identifier",
        example=UUIDFour.EXAMPLE,
    )
    cred_ex_id = fields.Str(
        required=False,
        description="Corresponding v2.0 credential exchange record identifier",
        example=UUIDFour.EXAMPLE,
    )
    # TODO: REMOVE THIS COMMENT AND SET DIF ITEMS BELOW
    item = fields.Dict(
        required=False,
        description="DIF item",
        example=UUIDFour.EXAMPLE,
    )
