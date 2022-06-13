"""Store revocation notification details until revocation is published."""

from typing import Optional, Sequence

from marshmallow import fields
from marshmallow.utils import EXCLUDE


from .....core.profile import ProfileSession
from .....messaging.models.base_record import BaseRecord, BaseRecordSchema
from .....messaging.valid import INDY_CRED_REV_ID, INDY_REV_REG_ID, UUID4
from .....storage.error import StorageNotFoundError, StorageDuplicateError
from ..messages.revoke import Revoke


class RevNotificationRecord(BaseRecord):
    """Revocation Notification Record."""

    class Meta:
        """RevNotificationRecord Meta."""

        schema_class = "RevNotificationRecordSchema"

    RECORD_TYPE = "revocation_notification"
    RECORD_ID_NAME = "revocation_notification_id"
    TAG_NAMES = {
        "rev_reg_id",
        "cred_rev_id",
        "connection_id",
        "version",
    }

    def __init__(
        self,
        *,
        revocation_notification_id: str = None,
        rev_reg_id: str = None,
        cred_rev_id: str = None,
        connection_id: str = None,
        thread_id: str = None,
        comment: str = None,
        version: str = None,
        **kwargs,
    ):
        """Construct record."""
        super().__init__(revocation_notification_id, **kwargs)
        self.rev_reg_id = rev_reg_id
        self.cred_rev_id = cred_rev_id
        self.connection_id = connection_id
        self.thread_id = thread_id
        self.comment = comment
        self.version = version

    @property
    def revocation_notification_id(self) -> Optional[str]:
        """Return record id."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Return record value."""
        return {prop: getattr(self, prop) for prop in ("thread_id", "comment")}

    @classmethod
    async def query_by_ids(
        cls,
        session: ProfileSession,
        cred_rev_id: str,
        rev_reg_id: str,
    ) -> "RevNotificationRecord":
        """Retrieve revocation notification record by cred rev id and/or rev reg id.

        Args:
            session: the profile session to use
            cred_rev_id: the cred rev id by which to filter
            rev_reg_id: the rev reg id by which to filter
        """
        tag_filter = {
            **{"version": "v1_0"},
            **{"cred_rev_id": cred_rev_id for _ in [""] if cred_rev_id},
            **{"rev_reg_id": rev_reg_id for _ in [""] if rev_reg_id},
        }

        result = await cls.query(session, tag_filter)
        if len(result) > 1:
            raise StorageDuplicateError(
                "More than one RevNotificationRecord was found for the given IDs"
            )
        if not result:
            raise StorageNotFoundError(
                "No RevNotificationRecord found for the given IDs"
            )
        return result[0]

    @classmethod
    async def query_by_rev_reg_id(
        cls,
        session: ProfileSession,
        rev_reg_id: str,
    ) -> Sequence["RevNotificationRecord"]:
        """Retrieve revocation notification records by rev reg id.

        Args:
            session: the profile session to use
            rev_reg_id: the rev reg id by which to filter
        """
        tag_filter = {
            **{"version": "v1_0"},
            **{"rev_reg_id": rev_reg_id for _ in [""] if rev_reg_id},
        }

        return await cls.query(session, tag_filter)

    def to_message(self):
        """Return a revocation notification constructed from this record."""
        if not self.thread_id:
            raise ValueError(
                "No thread ID set on revocation notification record, "
                "cannot create message"
            )
        return Revoke(
            thread_id=self.thread_id,
            comment=self.comment,
        )


class RevNotificationRecordSchema(BaseRecordSchema):
    """Revocation Notification Record Schema."""

    class Meta:
        """RevNotificationRecordSchema Meta."""

        model_class = "RevNotificationRecord"
        unknown = EXCLUDE

    rev_reg_id = fields.Str(
        required=False,
        description="Revocation registry identifier",
        **INDY_REV_REG_ID,
    )
    cred_rev_id = fields.Str(
        required=False,
        description="Credential revocation identifier",
        **INDY_CRED_REV_ID,
    )
    connection_id = fields.Str(
        description=(
            "Connection ID to which the revocation notification will be sent; "
            "required if notify is true"
        ),
        required=False,
        **UUID4,
    )
    thread_id = fields.Str(
        description=(
            "Thread ID of the credential exchange message thread resulting in "
            "the credential now being revoked; required if notify is true"
        ),
        required=False,
    )
    comment = fields.Str(
        description="Optional comment to include in revocation notification",
        required=False,
    )
    version = fields.Str(
        description="Version of Revocation Notification to send out",
        required=False,
    )
