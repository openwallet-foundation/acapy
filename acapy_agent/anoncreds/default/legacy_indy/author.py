"""Author specific for indy legacy."""

from typing import Optional

from aiohttp import web

from acapy_agent.connections.models.conn_record import ConnRecord
from acapy_agent.core.profile import Profile
from acapy_agent.messaging.models.base import BaseModelError
from acapy_agent.protocols.endorse_transaction.v1_0.util import get_endorser_connection_id
from acapy_agent.storage.error import StorageNotFoundError


async def get_endorser_info(
    profile: Profile, options: Optional[dict] = None
) -> tuple[str, str]:
    """Gets the endorser did for the current transaction."""
    options = options or {}
    endorser_connection_id = options.get("endorser_connection_id", None)
    if not endorser_connection_id:
        endorser_connection_id = await get_endorser_connection_id(profile)

    if not endorser_connection_id:
        raise web.HTTPForbidden(reason="No endorser connection found")

    try:
        async with profile.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(
                session, endorser_connection_id
            )
            endorser_info = await connection_record.metadata_get(session, "endorser_info")
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(
            reason=f"Connection for endorser with id {endorser_connection_id} not found"
        ) from err
    except BaseModelError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    if not endorser_info:
        raise web.HTTPForbidden(
            reason=(
                "Endorser Info is not set up in "
                "connection metadata for this connection record"
            )
        )
    if "endorser_did" not in endorser_info.keys():
        raise web.HTTPForbidden(
            reason=(
                '"endorser_did" is not set in "endorser_info" '
                "in connection metadata for this connection record"
            )
        )

    return endorser_info["endorser_did"], endorser_connection_id
