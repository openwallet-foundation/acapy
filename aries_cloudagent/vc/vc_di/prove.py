"""Verifiable Credential and Presentation proving methods."""

from typing import List


from ..ld_proofs import (
    AuthenticationProofPurpose,
    ProofPurpose,
    DocumentLoaderMethod,
    sign,
    LinkedDataProof,
    LinkedDataProofException,
    derive,
)
from ..ld_proofs.constants import CREDENTIALS_CONTEXT_V1_URL
from .models.credential import VerifiableCredentialSchema


async def create_signed_anoncreds_presentation(
    *,
    pres_definition: dict,
    presentation: dict,
    purpose: ProofPurpose = None,
    challenge: str = None,
    domain: str = None,
) -> dict:
    """Sign the presentation with the passed signature suite.

    Will set a default AuthenticationProofPurpose if no proof purpose is passed.

    Args:
        presentation (dict): The presentation to sign
        suite (LinkedDataProof): The signature suite to sign the presentation with
        document_loader (DocumentLoader): Document loader to use.
        purpose (ProofPurpose, optional): Purpose to use. Required if challenge is None
        challenge (str, optional): Challenge to use. Required if domain is None.
        domain (str, optional): Domain to use. Only used if purpose is None.

    Raises:
        LinkedDataProofException: When both purpose and challenge are not provided
            And when signing of the presentation fails

    Returns:
        dict: A verifiable presentation object

    """
    if not purpose and not challenge:
        raise LinkedDataProofException(
            'A "challenge" param is required when not providing a'
            ' "purpose" (for AuthenticationProofPurpose).'
        )
    if not purpose:
        purpose = AuthenticationProofPurpose(challenge=challenge, domain=domain)

    # validate structure of presentation
    pres_submission = presentation["presentation_submission"]
    descriptor_map = pres_submission["descriptor_map"]

    pres_name = pres_definition.get("name") if presentationDefinition.get("name") else 'Proof request'
    anonCredsProofRequest = {
        "version": '1.0',
        "name": pres_name,
        "nonce": nonce,
        "requested_attributes": {},
        "requested_predicates": {},
    }

"""
    const credentialsProve: AnonCredsCredentialProve[] = []
    const schemaIds = new Set<string>()
    const credentialDefinitionIds = new Set<string>()
    const credentialsWithMetadata: CredentialWithRevocationMetadata[] = []

    const hash = Hasher.hash(TypedArrayEncoder.fromString(challenge), 'sha-256')
    const nonce = new BigNumber(hash).toString().slice(0, 20)

    const anonCredsProofRequest: AnonCredsProofRequest = {
      version: '1.0',
      name: presentationDefinition.name ?? 'Proof request',
      nonce,
      requested_attributes: {},
      requested_predicates: {},
    }

    const nonRevoked = Math.floor(Date.now() / 1000)
    const nonRevokedInterval = { from: nonRevoked, to: nonRevoked }

    for (const descriptorMapObject of presentationSubmission.descriptor_map) {
      const descriptor: InputDescriptorV1 | InputDescriptorV2 | undefined = (
        presentationDefinition.input_descriptors as InputDescriptorV2[]
      ).find((descriptor) => descriptor.id === descriptorMapObject.id)

      if (!descriptor) {
        throw new Error(`Descriptor with id ${descriptorMapObject.id} not found in presentation definition`)
      }

      const referent = descriptorMapObject.id
      const attributeReferent = `${referent}_attribute`
      const predicateReferentBase = `${referent}_predicate`
      let predicateReferentIndex = 0

      const fields = descriptor.constraints?.fields
      if (!fields) throw new CredoError('Unclear mapping of constraint with no fields.')

      const { entryIndex, schemaId, credentialDefinitionId, revocationRegistryId, credential } =
        await this.getCredentialMetadataForDescriptor(agentContext, descriptorMapObject, credentials)

      schemaIds.add(schemaId)
      credentialDefinitionIds.add(credentialDefinitionId)

      const requiresRevocationStatus = this.descriptorRequiresRevocationStatus(descriptor)
      if (requiresRevocationStatus && !revocationRegistryId) {
        throw new CredoError('Selected credentials must be revocable but are not')
      }

      credentialsWithMetadata.push({
        credential,
        nonRevoked: requiresRevocationStatus ? nonRevokedInterval : undefined,
      })

      for (const field of fields) {
        const propertyName = this.getClaimNameForField(field)
        if (!propertyName) continue

        if (field.predicate) {
          if (!field.filter) throw new CredoError('Missing required predicate filter property.')
          const predicateTypeAndValues = this.getPredicateTypeAndValues(field.filter)
          for (const { predicateType, predicateValue } of predicateTypeAndValues) {
            const predicateReferent = `${predicateReferentBase}_${predicateReferentIndex++}`
            anonCredsProofRequest.requested_predicates[predicateReferent] = {
              name: propertyName,
              p_type: predicateType,
              p_value: predicateValue,
              restrictions: [{ cred_def_id: credentialDefinitionId }],
              non_revoked: requiresRevocationStatus ? nonRevokedInterval : undefined,
            }

            credentialsProve.push({ entryIndex, referent: predicateReferent, isPredicate: true, reveal: true })
          }
        } else {
          if (!anonCredsProofRequest.requested_attributes[attributeReferent]) {
            anonCredsProofRequest.requested_attributes[attributeReferent] = {
              names: [propertyName],
              restrictions: [{ cred_def_id: credentialDefinitionId }],
              non_revoked: requiresRevocationStatus ? nonRevokedInterval : undefined,
            }
          } else {
            const names = anonCredsProofRequest.requested_attributes[attributeReferent].names ?? []
            anonCredsProofRequest.requested_attributes[attributeReferent].names = [...names, propertyName]
          }

          credentialsProve.push({ entryIndex, referent: attributeReferent, isPredicate: false, reveal: true })
        }
      }
    }

    return { anonCredsProofRequest, credentialsWithMetadata, credentialsProve, schemaIds, credentialDefinitionIds }
"""

    return await sign(
        document=presentation,
        suite=suite,
        purpose=purpose,
        document_loader=document_loader,
    )
