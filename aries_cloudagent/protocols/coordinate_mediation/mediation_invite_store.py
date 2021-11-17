"""
Storage management for configuration-provided mediation invite.

Handle storage and retrieval of mediation invites provided through arguments.
Enables having the mediation invite config be the same
for `provision` and `starting` commands.
"""
import json
from typing import NamedTuple, Optional

from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.storage.error import StorageNotFoundError
from aries_cloudagent.storage.record import StorageRecord


class MediationInviteRecord(NamedTuple):
    """A record to store mediation invites and their freshness."""

    invite: str
    used: bool

    def to_json(self) -> str:
        """:return: The current record serialized into a json string."""
        return json.dumps({"invite": self.invite, "used": self.used})

    @staticmethod
    def from_json(json_invite_record: str) -> "MediationInviteRecord":
        """:return: a mediation invite record deserialized from a json string."""
        return MediationInviteRecord(**json.loads(json_invite_record))

    @staticmethod
    def unused(invite: str) -> "MediationInviteRecord":
        """
        :param invite: invite string as provided by the mediator.

        :return: An unused mediation invitation for the given invite string
        """
        return MediationInviteRecord(invite, False)


class NoDefaultMediationInviteException(Exception):
    """Raised if trying to mark a default invite as used when none exist."""


class MediationInviteStore:
    """Store and retrieve mediation invite configuration."""

    INVITE_RECORD_CATEGORY = "config"
    MEDIATION_INVITE_ID = "mediation_invite"

    def __init__(self, storage: BaseStorage):
        """:param storage: storage facility to be used to store mediation invitation."""
        self.__storage = storage

    async def __retrieve_record(self, key: str) -> Optional[StorageRecord]:
        try:
            return await self.__storage.get_record(self.INVITE_RECORD_CATEGORY, key)
        except StorageNotFoundError:
            return None

    async def store(
        self, mediation_invite: MediationInviteRecord
    ) -> MediationInviteRecord:
        """
        Store the mediator's invite for further use when starting the agent.

        Update the currently stored invite if one already exists.
        This assumes a new invite and as such, marks it as unused.

        :param mediation_invite: mediation invite url
        :return: stored mediation invite
        """
        current_invite_record = await self.__retrieve_record(self.MEDIATION_INVITE_ID)

        if current_invite_record is None:
            await self.__storage.add_record(
                StorageRecord(
                    type=self.INVITE_RECORD_CATEGORY,
                    id=self.MEDIATION_INVITE_ID,
                    value=mediation_invite.to_json(),
                )
            )
        else:
            await self.__storage.update_record(
                current_invite_record,
                mediation_invite.to_json(),
                tags=current_invite_record.tags,
            )

        return mediation_invite

    async def __retrieve(self) -> Optional[MediationInviteRecord]:
        """:return: the currently stored mediation invite url."""

        invite_record = await self.__retrieve_record(self.MEDIATION_INVITE_ID)
        return (
            MediationInviteRecord.from_json(invite_record.value)
            if invite_record is not None
            else None
        )

    async def __update_mediation_record(
        self, provided_mediation_invitation: str
    ) -> MediationInviteRecord:
        """
        Update the stored invitation when a new invitation is provided.

        Stored value is only updated if `provided_mediation_invitation` has changed.
        Updated record is marked as unused.

        :param provided_mediation_invitation: mediation invite provided by user
        :return: stored mediation invite
        """
        default_invite = await self.__retrieve()

        if default_invite != provided_mediation_invitation:
            default_invite = await self.store(
                MediationInviteRecord.unused(provided_mediation_invitation)
            )

        return default_invite

    async def mark_default_invite_as_used(self):
        """
        Mark the currently stored invitation as used if one exists.

        :raises NoDefaultMediationInviteException:
            if trying to mark invite as used when there is no invite stored.
        """
        record = await self.__retrieve()
        if not record:
            raise NoDefaultMediationInviteException(
                "No default mediation invite: cannot mark it as used."
            )

        updated_record = MediationInviteRecord(record.invite, used=True)
        await self.store(updated_record)

        return updated_record

    async def get_mediation_invite_record(
        self, provided_mediation_invitation: Optional[str]
    ) -> Optional[MediationInviteRecord]:
        """
        Provide the MediationInviteRecord to use/that was used for mediation.

        Returned record may have been used already.

        Stored record is updated if `provided_mediation_invitation` has changed.
        Updated record is marked as unused.

        :param provided_mediation_invitation: mediation invite provided by user
        :return: mediation invite to use/that was used to connect to the mediator. None if
            no invitation was provided/provisioned.
        """

        stored_invite = await self.__retrieve()

        if stored_invite is None and provided_mediation_invitation is None:
            return None
        elif stored_invite is None and provided_mediation_invitation is not None:
            return await self.store(
                MediationInviteRecord.unused(provided_mediation_invitation)
            )
        elif stored_invite is not None and provided_mediation_invitation is None:
            return stored_invite
        elif stored_invite is not None and provided_mediation_invitation is not None:
            return await self.__update_mediation_record(provided_mediation_invitation)
