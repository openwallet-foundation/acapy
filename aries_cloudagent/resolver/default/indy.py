"""Indy DID Resolver.

Resolution is performed using the IndyLedger class.
"""

from typing import Any, Mapping, Pattern

from pydid import DID, DIDDocumentBuilder
from pydid.verification_method import Ed25519VerificationKey2018, VerificationMethod

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ...ledger.endpoint_type import EndpointType
from ...ledger.error import LedgerError
from ...ledger.multiple_ledger.ledger_requests_executor import (
    GET_KEY_FOR_DID,
    IndyLedgerRequestsExecutor,
)
from ...messaging.valid import IndyDID
from ...multitenant.base import BaseMultitenantManager

from ..base import BaseDIDResolver, DIDNotFound, ResolverError, ResolverType


class NoIndyLedger(ResolverError):
    """Raised when there is no Indy ledger instance configured."""


class IndyDIDResolver(BaseDIDResolver):
    """Indy DID Resolver."""

    SERVICE_TYPE_DID_COMMUNICATION = "did-communication"
    SERVICE_TYPE_DIDCOMM = "DIDComm"
    SERVICE_TYPE_ENDPOINT = "endpoint"
    CONTEXT_DIDCOMM_V2 = "https://didcomm.org/messaging/contexts/v2"

    def __init__(self):
        """Initialize Indy Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Indy DID resolution."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported_did_regex of Indy DID Resolver."""
        return IndyDID.PATTERN

    def _add_endpoint_as_endpoint_value_pair(
        self,
        builder: DIDDocumentBuilder,
        endpoint: str,
        recipient_key: VerificationMethod,
    ):
        builder.service.add_didcomm(
            ident=self.SERVICE_TYPE_DID_COMMUNICATION,
            type_=self.SERVICE_TYPE_DID_COMMUNICATION,
            service_endpoint=endpoint,
            priority=1,
            recipient_keys=[recipient_key],
            routing_keys=[],
        )

    def _add_endpoint_as_map(
        self,
        builder: DIDDocumentBuilder,
        endpoint: Mapping[str, Any],
        recipient_key: VerificationMethod,
    ):
        types = endpoint.get("types", [self.SERVICE_TYPE_DID_COMMUNICATION])
        routing_keys = endpoint.get("routingKeys", [])
        endpoint_url = endpoint.get("endpoint")
        if not endpoint_url:
            raise ValueError("endpoint url not found in endpoint attrib")

        if self.SERVICE_TYPE_DIDCOMM in types:
            builder.service.add(
                ident="#didcomm-1",
                type_=self.SERVICE_TYPE_DIDCOMM,
                service_endpoint=endpoint_url,
                recipient_keys=[recipient_key.id],
                routing_keys=routing_keys,
                accept=["didcomm/v2"],
            )
            builder.context.append(self.CONTEXT_DIDCOMM_V2)
        if self.SERVICE_TYPE_DID_COMMUNICATION in types:
            builder.service.add(
                ident="did-communication",
                type_=self.SERVICE_TYPE_DID_COMMUNICATION,
                service_endpoint=endpoint_url,
                priority=1,
                routing_keys=routing_keys,
                recipient_keys=[recipient_key.id],
                accept=["didcomm/aip2;env=rfc19"],
            )
        if self.SERVICE_TYPE_ENDPOINT in types:
            builder.service.add(
                ident="endpoint",
                service_endpoint=endpoint_url,
                type_=self.SERVICE_TYPE_ENDPOINT,
            )

    async def _resolve(self, profile: Profile, did: str) -> dict:
        """Resolve an indy DID."""
        multitenant_mgr = profile.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(profile)
        else:
            ledger_exec_inst = profile.inject(IndyLedgerRequestsExecutor)
        ledger = (
            await ledger_exec_inst.get_ledger_for_identifier(
                did,
                txn_record_type=GET_KEY_FOR_DID,
            )
        )[1]
        if not ledger:
            raise NoIndyLedger("No Indy ledger instance is configured.")

        try:
            async with ledger:
                recipient_key = await ledger.get_key_for_did(did)
                endpoints = await ledger.get_all_endpoints_for_did(did)
        except LedgerError as err:
            raise DIDNotFound(f"DID {did} could not be resolved") from err

        builder = DIDDocumentBuilder(DID(did))

        vmethod = builder.verification_method.add(
            Ed25519VerificationKey2018, ident="key-1", public_key_base58=recipient_key
        )
        builder.authentication.reference(vmethod.id)
        builder.assertion_method.reference(vmethod.id)
        if endpoints:
            for type_, endpoint in endpoints.items():
                if type_ == EndpointType.ENDPOINT.indy:
                    if isinstance(endpoint, dict):
                        self._add_endpoint_as_map(builder, endpoint, vmethod)
                    else:
                        self._add_endpoint_as_endpoint_value_pair(
                            builder, endpoint, vmethod
                        )
                else:
                    # Accept all service types for now, i.e. profile, linked_domains
                    builder.service.add(
                        ident=type_,
                        type_=type_,
                        service_endpoint=endpoint,
                    )

        result = builder.build()
        return result.serialize()
