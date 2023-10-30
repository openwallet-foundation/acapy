"""Endorser utilities."""


from ....connections.models.conn_record import ConnRecord
from ....core.profile import Profile


def is_author_role(profile: Profile):
    """Check if agent is running in author mode."""
    return profile.settings.get_value("endorser.author")


async def get_endorser_connection_id(profile: Profile):
    """Determine default endorser connection for author."""
    if not is_author_role(profile):
        return None

    endorser_alias = profile.settings.get_value("endorser.endorser_alias")
    if not endorser_alias:
        return None
    try:
        async with profile.session() as session:
            connection_records = await ConnRecord.retrieve_by_alias(
                session, endorser_alias
            )
            connection_id = connection_records[0].connection_id
            return connection_id
    except Exception:
        return None
