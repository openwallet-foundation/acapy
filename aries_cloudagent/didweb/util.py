from pydid import DIDDocument
from ..core.profile import ProfileSession
from ..storage.base import (
    BaseStorage,
    StorageRecord,
    StorageNotFoundError,
)

DID_WEB_RECORD_TYPE = "did_web_did_document"


async def retrieve_did_document(
    session: ProfileSession
) -> DIDDocument:
    """Retrieve DID document."""
    storage = session.inject(BaseStorage)
    try:
        record = await storage.find_record(
            DID_WEB_RECORD_TYPE
        )
    except StorageNotFoundError:
        record = None
    return DIDDocument.from_json(record.value) if record else None


async def save_did_document(
    did_document: DIDDocument, session: ProfileSession
):
    """Save a DID document"""
    storage = session.inject(BaseStorage)
    try:
        record = await storage.find_record(
            DID_WEB_RECORD_TYPE,
            {"did_doc": "x"}
        )
    except StorageNotFoundError:
        if did_document:
            record = StorageRecord(
                type=DID_WEB_RECORD_TYPE,
                value=did_document.to_json(),
                tags={"did_doc": "x"}
            )
            await storage.add_record(record)
    else:
        if did_document:
            await storage.update_record(
                record, did_document.to_json(), {"did_doc": "x"}
            )
        else:
            await storage.delete_record(record)
