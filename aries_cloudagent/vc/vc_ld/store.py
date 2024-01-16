from ...admin.request_context import AdminRequestContext
from ...storage.vc_holder.base import VCHolder
from ...storage.vc_holder.vc_record import VCRecord
from ...vc.vc_ld import VerifiableCredential
from ...vc.ld_proofs import DocumentLoader
from pyld import jsonld
from pyld.jsonld import JsonLdProcessor


async def store_credential(
    credential: VerifiableCredential,
    document_loader: DocumentLoader,
    context: AdminRequestContext,
    cred_id: str = None,
):
    """
    Store a verifiable credential.

    """
    # Saving expanded type as a cred_tag
    expanded = jsonld.expand(
        credential.serialize(), options={"documentLoader": document_loader}
    )
    types = JsonLdProcessor.get_values(
        expanded[0],
        "@type",
    )
    vc_record = VCRecord(
        contexts=credential.context_urls,
        expanded_types=types,
        issuer_id=credential.issuer_id,
        subject_ids=credential.credential_subject_ids,
        schema_ids=[],  # Schemas not supported yet
        proof_types=[credential.proof.type],
        cred_value=credential.serialize(),
        given_id=credential.id,
        record_id=cred_id,
        cred_tags=None,  # Tags should be derived from credential values
    )

    async with context.profile.session() as session:
        vc_holder = session.inject(VCHolder)

        await vc_holder.store_credential(vc_record)
