"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
import json
from dataclasses import dataclass
from os import getenv
from secrets import randbelow, token_hex
from typing import Any, Dict, List, Mapping, Optional, Tuple, Type, Union
from uuid import uuid4

from acapy_controller import Controller
from acapy_controller.controller import Minimal, MinType
from acapy_controller.logging import logging_to_stdout
from acapy_controller.models import V20PresExRecord, V20PresExRecordList
from acapy_controller.protocols import (
    DIDResult,
    didexchange,
    params,
)
from aiohttp import ClientSession

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")
INDY = getenv("INDY", "http://indy:3001")


def summary(presentation: V20PresExRecord) -> str:
    """Summarize a presentation exchange record."""
    request = presentation.pres_request
    return "Summary: " + json.dumps(
        {
            "state": presentation.state,
            "verified": presentation.verified,
            "presentation_request": request.model_dump(by_alias=True)
            if request
            else None,
        },
        indent=2,
        sort_keys=True,
    )


@dataclass
class SchemaResult(Minimal):
    """Schema result."""

    schema_state: dict


@dataclass
class CredDefResult(Minimal):
    """Credential definition result."""

    credential_definition_state: dict


@dataclass
class V20CredExRecord(Minimal):
    """V2.0 credential exchange record."""

    state: str
    cred_ex_id: str
    connection_id: str
    thread_id: str


@dataclass
class V20CredExRecordAnoncreds(Minimal):
    """V2.0 credential exchange record anoncreds."""

    rev_reg_id: Optional[str] = None
    cred_rev_id: Optional[str] = None


@dataclass
class V20CredExRecordDetail(Minimal):
    """V2.0 credential exchange record detail."""

    cred_ex_record: V20CredExRecord
    anoncreds: Optional[V20CredExRecordAnoncreds] = None


@dataclass
class ProofRequest(Minimal):
    """Proof request."""

    requested_attributes: Dict[str, Any]
    requested_predicates: Dict[str, Any]


@dataclass
class PresSpec(Minimal):
    """Presentation specification."""

    requested_attributes: Dict[str, Any]
    requested_predicates: Dict[str, Any]
    self_attested_attributes: Dict[str, Any]


@dataclass
class CredInfo(Minimal):
    """Credential information."""

    referent: str
    attrs: Dict[str, Any]


@dataclass
class CredPrecis(Minimal):
    """Credential precis."""

    cred_info: CredInfo
    presentation_referents: List[str]

    @classmethod
    def deserialize(cls: Type[MinType], value: Mapping[str, Any]) -> MinType:
        """Deserialize the credential precis."""
        value = dict(value)
        if cred_info := value.get("cred_info"):
            value["cred_info"] = CredInfo.deserialize(cred_info)
        return super().deserialize(value)


def auto_select_credentials_for_presentation_request(
    presentation_request: Union[ProofRequest, dict],
    relevant_creds: List[CredPrecis],
) -> PresSpec:
    """Select credentials to use for presentation automatically."""
    if isinstance(presentation_request, dict):
        presentation_request = ProofRequest.deserialize(presentation_request)

    requested_attributes = {}
    for pres_referrent in presentation_request.requested_attributes.keys():
        for cred_precis in relevant_creds:
            if pres_referrent in cred_precis.presentation_referents:
                requested_attributes[pres_referrent] = {
                    "cred_id": cred_precis.cred_info.referent,
                    "revealed": True,
                }
    requested_predicates = {}
    for pres_referrent in presentation_request.requested_predicates.keys():
        for cred_precis in relevant_creds:
            if pres_referrent in cred_precis.presentation_referents:
                requested_predicates[pres_referrent] = {
                    "cred_id": cred_precis.cred_info.referent,
                }

    return PresSpec.deserialize(
        {
            "requested_attributes": requested_attributes,
            "requested_predicates": requested_predicates,
            "self_attested_attributes": {},
        }
    )


async def anoncreds_issue_credential_v2(
    issuer: Controller,
    holder: Controller,
    issuer_connection_id: str,
    holder_connection_id: str,
    cred_def_id: str,
    attributes: Mapping[str, str],
) -> Tuple[V20CredExRecordDetail, V20CredExRecordDetail]:
    """Issue an anoncreds credential using issue-credential/2.0.

    Issuer and holder should already be connected.
    """

    issuer_cred_ex = await issuer.post(
        "/issue-credential-2.0/send-offer",
        json={
            "auto_issue": False,
            "auto_remove": False,
            "comment": "Credential from minimal example",
            "trace": False,
            "connection_id": issuer_connection_id,
            "filter": {"anoncreds": {"cred_def_id": cred_def_id}},
            "credential_preview": {
                "type": "issue-credential-2.0/2.0/credential-preview",  # pyright: ignore
                "attributes": [
                    {
                        "mime_type": None,
                        "name": name,
                        "value": value,
                    }
                    for name, value in attributes.items()
                ],
            },
        },
        response=V20CredExRecord,
    )
    issuer_cred_ex_id = issuer_cred_ex.cred_ex_id

    holder_cred_ex = await holder.event_with_values(
        topic="issue_credential_v2_0",
        event_type=V20CredExRecord,
        connection_id=holder_connection_id,
        state="offer-received",
    )
    holder_cred_ex_id = holder_cred_ex.cred_ex_id

    await holder.post(
        f"/issue-credential-2.0/records/{holder_cred_ex_id}/send-request",
        response=V20CredExRecord,
    )

    await issuer.event_with_values(
        topic="issue_credential_v2_0",
        cred_ex_id=issuer_cred_ex_id,
        state="request-received",
    )

    await issuer.post(
        f"/issue-credential-2.0/records/{issuer_cred_ex_id}/issue",
        json={},
        response=V20CredExRecordDetail,
    )

    await holder.event_with_values(
        topic="issue_credential_v2_0",
        cred_ex_id=holder_cred_ex_id,
        state="credential-received",
    )

    await holder.post(
        f"/issue-credential-2.0/records/{holder_cred_ex_id}/store",
        json={},
        response=V20CredExRecordDetail,
    )
    issuer_cred_ex = await issuer.event_with_values(
        topic="issue_credential_v2_0",
        event_type=V20CredExRecord,
        cred_ex_id=issuer_cred_ex_id,
        state="done",
    )
    issuer_anoncreds_record = await issuer.event_with_values(
        topic="issue_credential_v2_0_anoncreds",
        event_type=V20CredExRecordAnoncreds,
    )

    holder_cred_ex = await holder.event_with_values(
        topic="issue_credential_v2_0",
        event_type=V20CredExRecord,
        cred_ex_id=holder_cred_ex_id,
        state="done",
    )
    holder_record = await holder.event_with_values(
        topic="issue_credential_v2_0_anoncreds",
        event_type=V20CredExRecordAnoncreds,
    )

    return (
        V20CredExRecordDetail(
            cred_ex_record=issuer_cred_ex, anoncreds=issuer_anoncreds_record
        ),
        V20CredExRecordDetail(
            cred_ex_record=holder_cred_ex,
            anoncreds=holder_record,
        ),
    )


async def anoncreds_present_proof_v2(
    holder: Controller,
    verifier: Controller,
    holder_connection_id: str,
    verifier_connection_id: str,
    *,
    name: Optional[str] = None,
    version: Optional[str] = None,
    comment: Optional[str] = None,
    requested_attributes: Optional[List[Mapping[str, Any]]] = None,
    requested_predicates: Optional[List[Mapping[str, Any]]] = None,
    non_revoked: Optional[Mapping[str, int]] = None,
):
    """Present an Anoncreds credential using present proof v2."""
    verifier_pres_ex = await verifier.post(
        "/present-proof-2.0/send-request",
        json={
            "auto_verify": False,
            "comment": comment or "Presentation request from minimal",
            "connection_id": verifier_connection_id,
            "presentation_request": {
                "anoncreds": {
                    "name": name or "proof",
                    "version": version or "0.1.0",
                    "nonce": str(randbelow(10**10)),
                    "requested_attributes": {
                        str(uuid4()): attr for attr in requested_attributes or []
                    },
                    "requested_predicates": {
                        str(uuid4()): pred for pred in requested_predicates or []
                    },
                    "non_revoked": (non_revoked if non_revoked else None),
                },
            },
            "trace": False,
        },
        response=V20PresExRecord,
    )
    verifier_pres_ex_id = verifier_pres_ex.pres_ex_id

    holder_pres_ex = await holder.event_with_values(
        topic="present_proof_v2_0",
        event_type=V20PresExRecord,
        connection_id=holder_connection_id,
        state="request-received",
    )
    assert holder_pres_ex.pres_request
    holder_pres_ex_id = holder_pres_ex.pres_ex_id

    relevant_creds = await holder.get(
        f"/present-proof-2.0/records/{holder_pres_ex_id}/credentials",
        response=List[CredPrecis],
    )
    assert holder_pres_ex.by_format.pres_request
    proof_request = holder_pres_ex.by_format.pres_request["anoncreds"]
    pres_spec = auto_select_credentials_for_presentation_request(
        proof_request, relevant_creds
    )
    await holder.post(
        f"/present-proof-2.0/records/{holder_pres_ex_id}/send-presentation",
        json={
            "anoncreds": pres_spec.serialize(),
            "trace": False,
        },
        response=V20PresExRecord,
    )

    await verifier.event_with_values(
        topic="present_proof_v2_0",
        event_type=V20PresExRecord,
        pres_ex_id=verifier_pres_ex_id,
        state="presentation-received",
    )
    await verifier.post(
        f"/present-proof-2.0/records/{verifier_pres_ex_id}/verify-presentation",
        json={},
        response=V20PresExRecord,
    )
    verifier_pres_ex = await verifier.event_with_values(
        topic="present_proof_v2_0",
        event_type=V20PresExRecord,
        pres_ex_id=verifier_pres_ex_id,
        state="done",
    )

    holder_pres_ex = await holder.event_with_values(
        topic="present_proof_v2_0",
        event_type=V20PresExRecord,
        pres_ex_id=holder_pres_ex_id,
        state="done",
    )

    return holder_pres_ex, verifier_pres_ex


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(
        base_url=BOB
    ) as bob, Controller(base_url=INDY) as indy:
        # Connecting
        alice_conn, bob_conn = await didexchange(alice, bob)

        # Issuance prep
        config = (await alice.get("/status/config"))["config"]
        genesis_url = config.get("ledger.genesis_url")
        public_did = (await alice.get("/wallet/did/public", response=DIDResult)).result
        if not public_did:
            public_did = (
                await alice.post(
                    "/wallet/did/create",
                    json={"method": "sov", "options": {"key_type": "ed25519"}},
                    response=DIDResult,
                )
            ).result
            assert public_did

            async with ClientSession() as session:
                register_url = genesis_url.replace("/genesis", "/register")
                async with session.post(
                    register_url,
                    json={
                        "did": public_did.did,
                        "verkey": public_did.verkey,
                        "alias": None,
                        "role": "ENDORSER",
                    },
                ) as resp:
                    assert resp.ok

            await alice.post("/wallet/did/public", params=params(did=public_did.did))

        schema = await alice.post(
            "/anoncreds/schema",
            json={
                "schema": {
                    "name": "anoncreds-test-" + token_hex(8),
                    "version": "1.0",
                    "attrNames": ["firstname", "lastname"],
                    "issuerId": public_did.did,
                }
            },
            response=SchemaResult,
        )
        cred_def = await alice.post(
            "/anoncreds/credential-definition",
            json={
                "credential_definition": {
                    "issuerId": schema.schema_state["schema"]["issuerId"],
                    "schemaId": schema.schema_state["schema_id"],
                    "tag": token_hex(8),
                },
                "options": {
                    "revocation_registry_size": 2000,
                    "support_revocation": True,
                },
            },
            response=CredDefResult,
        )

        # Issue a credential
        alice_cred_ex, _ = await anoncreds_issue_credential_v2(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_state["credential_definition_id"],
            {"firstname": "Bob", "lastname": "Builder"},
        )

        # Present the the credential's attributes
        await anoncreds_present_proof_v2(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[{"name": "firstname"}],
        )

        # Revoke credential
        await alice.post(
            url="/anoncreds/revocation/revoke",
            json={
                "connection_id": alice_conn.connection_id,
                "rev_reg_id": alice_cred_ex.anoncreds.rev_reg_id,
                "cred_rev_id": alice_cred_ex.anoncreds.cred_rev_id,
                "publish": True,
                "notify": True,
                "notify_version": "v1_0",
            },
        )

        await bob.record(topic="revocation-notification")

        # Request proof, no interval
        await anoncreds_present_proof_v2(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[
                {
                    "name": "firstname",
                    "restrictions": [
                        {
                            "cred_def_id": cred_def.credential_definition_state[
                                "credential_definition_id"
                            ]
                        }
                    ],
                }
            ],
        )

        # Test a non-anoncreds agent using old indy format

        # Connecting
        alice_conn, indy_conn = await didexchange(alice, indy)

        # Issue a credential
        alice_cred_ex, _ = await anoncreds_issue_credential_v2(
            alice,
            indy,
            alice_conn.connection_id,
            indy_conn.connection_id,
            cred_def.credential_definition_state["credential_definition_id"],
            {"firstname": "Indy", "lastname": "Builder"},
        )

        # Present the the credential's attributes
        await anoncreds_present_proof_v2(
            indy,
            alice,
            indy_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[{"name": "firstname"}],
        )

        # Query presentations
        presentations = await alice.get(
            "/present-proof-2.0/records",
            response=V20PresExRecordList,
        )

        # Presentation summary
        for _, pres in enumerate(presentations.results):
            print(summary(pres))

        # Revoke credential
        await alice.post(
            url="/anoncreds/revocation/revoke",
            json={
                "connection_id": alice_conn.connection_id,
                "rev_reg_id": alice_cred_ex.anoncreds.rev_reg_id,
                "cred_rev_id": alice_cred_ex.anoncreds.cred_rev_id,
                "publish": True,
                "notify": True,
                "notify_version": "v1_0",
            },
        )

        await indy.record(topic="revocation-notification")


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
