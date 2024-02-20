"""Common endorsement utilities."""

import logging

from ..connections.models.conn_record import ConnRecord
from ..core.profile import Profile
from ..protocols.connections.v1_0.manager import ConnectionManager
from ..protocols.connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
)
from ..protocols.endorse_transaction.v1_0.manager import TransactionManager
from ..protocols.endorse_transaction.v1_0.transaction_jobs import TransactionJob
from ..protocols.endorse_transaction.v1_0.util import (
    get_endorser_connection_id,
    is_author_role,
)
from ..protocols.out_of_band.v1_0.manager import OutOfBandManager
from ..protocols.out_of_band.v1_0.messages.invitation import InvitationMessage

LOGGER = logging.getLogger(__name__)


async def attempt_auto_author_with_endorser_setup(profile: Profile):
    """Automatically setup the author's endorser connection if possible."""

    if not is_author_role(profile):
        return

    endorser_invitation = profile.settings.get_value("endorser.endorser_invitation")
    if not endorser_invitation:
        LOGGER.info("No endorser invitation, can't connect automatically.")
        return

    endorser_alias = profile.settings.get_value("endorser.endorser_alias")
    if not endorser_alias:
        LOGGER.info("No endorser alias, alias is required if invitation is specified.")
        return

    connection_id = await get_endorser_connection_id(profile)
    if connection_id:
        LOGGER.info("Connected to endorser from previous connection.")
        return

    endorser_did = profile.settings.get_value("endorser.endorser_public_did")
    if not endorser_did:
        LOGGER.info(
            "No endorser DID, can connect, but can't setup connection metadata."
        )
        return

    try:
        # OK, we are an author, we have no endorser connection but we have enough info
        # to automatically initiate the connection
        invite = InvitationMessage.from_url(endorser_invitation)
        if invite:
            oob_mgr = OutOfBandManager(profile)
            oob_record = await oob_mgr.receive_invitation(
                invitation=invite,
                auto_accept=True,
                alias=endorser_alias,
            )
            async with profile.session() as session:
                conn_record = await ConnRecord.retrieve_by_id(
                    session, oob_record.connection_id
                )
        else:
            invite = ConnectionInvitation.from_url(endorser_invitation)
            if invite:
                conn_mgr = ConnectionManager(profile)
                conn_record = await conn_mgr.receive_invitation(
                    invitation=invite,
                    auto_accept=True,
                    alias=endorser_alias,
                )
            else:
                raise Exception(
                    "Failed to establish endorser connection, invalid "
                    "invitation format."
                )

        # configure the connection role and info (don't need to wait for the connection)
        transaction_mgr = TransactionManager(profile)
        await transaction_mgr.set_transaction_my_job(
            record=conn_record,
            transaction_my_job=TransactionJob.TRANSACTION_AUTHOR.name,
        )

        async with profile.session() as session:
            value = await conn_record.metadata_get(session, "endorser_info")
            if value:
                value["endorser_did"] = endorser_did
                value["endorser_name"] = endorser_alias
            else:
                value = {"endorser_did": endorser_did, "endorser_name": endorser_alias}
            await conn_record.metadata_set(session, key="endorser_info", value=value)

        LOGGER.info(
            "Successfully connected to endorser from invitation, and setup connection metadata."  # noqa: E501
        )

    except Exception:
        LOGGER.info(
            "Error accepting endorser invitation/configuring endorser connection"
        )
