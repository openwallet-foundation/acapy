"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
import json
from datetime import date
from os import getenv
from uuid import uuid4

from acapy_controller import Controller
from acapy_controller.controller import ControllerError
from acapy_controller.logging import logging_to_stdout, pause_for_input, section
from acapy_controller.models import DIDResult, V20PresExRecord
from acapy_controller.protocols import (
    didexchange,
    jsonld_issue_credential,
    params,
)
from aiohttp import ClientSession
from examples.util import jsonld_present_proof_v2

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


def presentation_summary(pres_ex: V20PresExRecord):
    """Summarize a presentation."""
    pres_ex_dict = pres_ex.dict(exclude_none=True, exclude_unset=True)
    return json.dumps(
        {
            key: pres_ex_dict.get(key)
            for key in (
                "verified",
                "state",
                "role",
                "connection_id",
                "pres_request",
                "pres",
            )
        },
        indent=2,
    )


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        with section("Establish connection"):
            alice_conn, bob_conn = await didexchange(alice, bob)

        with section("Prepare for issuance"):
            with section("Issuer prepares issuing DIDs", character="-"):
                config = (await alice.get("/status/config"))["config"]
                genesis_url = config.get("ledger.genesis_url")
                public_did = (
                    await alice.get("/wallet/did/public", response=DIDResult)
                ).result
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

                    await alice.post(
                        "/wallet/did/public", params=params(did=public_did.did)
                    )

                p256_alice_did_res = (
                    await alice.post(
                        "/wallet/did/create",
                        json={"method": "key", "options": {"key_type": "p256"}},
                    )
                )["result"]
                assert p256_alice_did_res
                p256_alice_did = p256_alice_did_res["did"]

                bls_alice_did_res = (
                    await alice.post(
                        "/wallet/did/create",
                        json={"method": "key", "options": {"key_type": "bls12381g2"}},
                    )
                )["result"]
                assert bls_alice_did_res
                bls_alice_did = bls_alice_did_res["did"]

            with section("Recipient prepares subject DIDs", character="-"):
                ed25519_bob_did = (
                    await bob.post(
                        "/wallet/did/create",
                        json={"method": "key", "options": {"key_type": "ed25519"}},
                        response=DIDResult,
                    )
                ).result
                assert ed25519_bob_did
                p256_bob_did_res = (
                    await bob.post(
                        "/wallet/did/create",
                        json={"method": "key", "options": {"key_type": "p256"}},
                    )
                )["result"]
                assert p256_bob_did_res
                p256_bob_did = p256_bob_did_res["did"]
                bls_bob_did_res = (
                    await bob.post(
                        "/wallet/did/create",
                        json={"method": "key", "options": {"key_type": "bls12381g2"}},
                    )
                )["result"]
                assert bls_bob_did_res
                bls_bob_did = bls_bob_did_res["did"]

        pause_for_input()

        with section("Issue example credential using Public Issuer ED25519 Signature"):
            issuer_cred_ex, holder_cred_ex = await jsonld_issue_credential(
                alice,
                bob,
                alice_conn.connection_id,
                bob_conn.connection_id,
                credential={
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://w3id.org/citizenship/v1",
                    ],
                    "type": ["VerifiableCredential", "PermanentResident"],
                    "issuer": "did:sov:" + public_did.did,
                    "issuanceDate": str(date.today()),
                    "credentialSubject": {
                        "type": ["PermanentResident"],
                        "id": ed25519_bob_did.did,
                        "givenName": "Bob",
                        "familyName": "Builder",
                        "gender": "Male",
                        "birthCountry": "Bahamas",
                        "birthDate": "1958-07-17",
                    },
                },
                options={"proofType": "Ed25519Signature2018"},
            )

        pause_for_input()

        with section("Present example ED25519 credential"):
            alice_pres_ex, bob_pres_ex = await jsonld_present_proof_v2(
                alice,
                bob,
                alice_conn.connection_id,
                bob_conn.connection_id,
                presentation_definition={
                    "input_descriptors": [
                        {
                            "id": "citizenship_input_1",
                            "name": "EU Driver's License",
                            "schema": [
                                {
                                    "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"  # noqa: E501
                                },
                                {
                                    "uri": "https://w3id.org/citizenship#PermanentResident"  # noqa: E501
                                },
                            ],
                            "constraints": {
                                "is_holder": [
                                    {
                                        "directive": "required",
                                        "field_id": [
                                            "1f44d55f-f161-4938-a659-f8026467f126"
                                        ],
                                    }
                                ],
                                "fields": [
                                    {
                                        "id": "1f44d55f-f161-4938-a659-f8026467f126",
                                        "path": ["$.credentialSubject.familyName"],
                                        "purpose": "The claim must be from one of the specified issuers",  # noqa: E501
                                        "filter": {"const": "Builder"},
                                    },
                                    {
                                        "path": ["$.credentialSubject.givenName"],
                                        "purpose": "The claim must be from one of the specified issuers",  # noqa: E501
                                    },
                                ],
                            },
                        }
                    ],
                    "id": str(uuid4()),
                    "format": {"ldp_vp": {"proof_type": ["Ed25519Signature2018"]}},
                },
                domain="test-degree",
            )
        with section("Presentation summary", character="-"):
            print(presentation_summary(alice_pres_ex))

        pause_for_input()

        with section("Issue example credential using P256 Signature"):
            issuer_cred_ex, holder_cred_ex = await jsonld_issue_credential(
                alice,
                bob,
                alice_conn.connection_id,
                bob_conn.connection_id,
                credential={
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://w3id.org/citizenship/v1",
                    ],
                    "type": ["VerifiableCredential", "PermanentResident"],
                    "issuer": p256_alice_did,
                    "issuanceDate": str(date.today()),
                    "credentialSubject": {
                        "type": ["PermanentResident"],
                        "id": p256_bob_did,
                        "givenName": "Bob",
                        "familyName": "Builder",
                        "gender": "Male",
                        "birthCountry": "Bahamas",
                        "birthDate": "1958-07-17",
                    },
                },
                options={"proofType": "EcdsaSecp256r1Signature2019"},
            )

        pause_for_input()

        with section("Present example P256 credential"):
            alice_pres_ex, bob_pres_ex = await jsonld_present_proof_v2(
                alice,
                bob,
                alice_conn.connection_id,
                bob_conn.connection_id,
                presentation_definition={
                    "input_descriptors": [
                        {
                            "id": "citizenship_input_1",
                            "name": "EU Driver's License",
                            "schema": [
                                {
                                    "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"  # noqa: E501
                                },
                                {
                                    "uri": "https://w3id.org/citizenship#PermanentResident"  # noqa: E501
                                },
                            ],
                            "constraints": {
                                "is_holder": [
                                    {
                                        "directive": "required",
                                        "field_id": [
                                            "1f44d55f-f161-4938-a659-f8026467f126"
                                        ],
                                    }
                                ],
                                "fields": [
                                    {
                                        "id": "1f44d55f-f161-4938-a659-f8026467f126",
                                        "path": ["$.credentialSubject.familyName"],
                                        "purpose": "The claim must be from one of the specified issuers",  # noqa: E501
                                        "filter": {"const": "Builder"},
                                    },
                                    {
                                        "path": ["$.issuer"],
                                        "purpose": "The claim must be from one of the specified issuers",  # noqa: E501
                                        "filter": {"const": p256_alice_did},
                                    },
                                    {
                                        "path": ["$.credentialSubject.givenName"],
                                        "purpose": "The claim must be from one of the specified issuers",  # noqa: E501
                                    },
                                ],
                            },
                        }
                    ],
                    "id": str(uuid4()),
                    "format": {"ldp_vp": {"proof_type": ["EcdsaSecp256r1Signature2019"]}},
                },
                domain="test-degree",
            )
        with section("Presentation summary", character="-"):
            print(presentation_summary(alice_pres_ex))

        pause_for_input()

        with section("Issue ED25519 Credential with quick context"):
            issuer_cred_ex, holder_cred_ex = await jsonld_issue_credential(
                alice,
                bob,
                alice_conn.connection_id,
                bob_conn.connection_id,
                credential={
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        {
                            "ex": "https://example.com/examples#",
                            "TableTennisTournamentWin": "ex:TableTennisTournamentWin",
                            "dateWon": "ex:dateWon",
                        },
                    ],
                    "type": ["VerifiableCredential", "TableTennisTournamentWin"],
                    "issuer": "did:sov:" + public_did.did,
                    "issuanceDate": str(date.today()),
                    "credentialSubject": {
                        "id": ed25519_bob_did.did,
                        "dateWon": str(date.today()),
                    },
                },
                options={"proofType": "Ed25519Signature2018"},
            )

        pause_for_input()

        with section("Present ED25519 quick context credential"):
            alice_pres_ex, bob_pres_ex = await jsonld_present_proof_v2(
                alice,
                bob,
                alice_conn.connection_id,
                bob_conn.connection_id,
                presentation_definition={
                    "input_descriptors": [
                        {
                            "id": "ttt_win_input_1",
                            "name": "TableTennisTournamentWin",
                            "schema": [
                                {
                                    "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"  # noqa: E501
                                },
                                {
                                    "uri": "https://example.com/examples#TableTennisTournamentWin"  # noqa: E501
                                },
                            ],
                            "constraints": {
                                "is_holder": [
                                    {
                                        "directive": "required",
                                        "field_id": [
                                            "1f44d55f-f161-4938-a659-f8026467f126"
                                        ],
                                    }
                                ],
                                "fields": [
                                    {
                                        "id": "1f44d55f-f161-4938-a659-f8026467f126",
                                        "path": ["$.credentialSubject.dateWon"],
                                        "purpose": "Get proof of win on date",  # noqa: E501
                                    },
                                ],
                            },
                        }
                    ],
                    "id": str(uuid4()),
                    "format": {"ldp_vp": {"proof_type": ["Ed25519Signature2018"]}},
                },
                domain="test-degree",
            )
        with section("Presentation summary", character="-"):
            print(presentation_summary(alice_pres_ex))

        pause_for_input()

        with section("Issue BBS+ Credential"):
            try:
                issuer_cred_ex, holder_cred_ex = await jsonld_issue_credential(
                    alice,
                    bob,
                    alice_conn.connection_id,
                    bob_conn.connection_id,
                    credential={
                        "@context": [
                            "https://www.w3.org/2018/credentials/v1",
                            {
                                "ex": "https://example.com/examples#",
                                "Employment": "ex:Employment",
                                "dateHired": "ex:dateHired",
                                "clearance": "ex:clearance",
                            },
                        ],
                        "type": ["VerifiableCredential", "Employment"],
                        "issuer": bls_alice_did,
                        "issuanceDate": str(date.today()),
                        "credentialSubject": {
                            "id": bls_bob_did,
                            "dateHired": str(date.today()),
                            "clearance": 1,
                        },
                    },
                    options={"proofType": "BbsBlsSignature2020"},
                )
            except ControllerError as err:
                print(f"Skipping BBS+ flow due to runtime capability/error: {err}")
                return

        pause_for_input()

        with section("Present BBS+ Credential with SD"):
            alice_pres_ex, bob_pres_ex = await jsonld_present_proof_v2(
                alice,
                bob,
                alice_conn.connection_id,
                bob_conn.connection_id,
                presentation_definition={
                    "input_descriptors": [
                        {
                            "id": "building_access_1",
                            "name": "BuildingAccess",
                            "schema": [
                                {
                                    "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"  # noqa: E501
                                },
                                {"uri": "https://example.com/examples#Employment"},
                            ],
                            "constraints": {
                                "limit_disclosure": "required",
                                "is_holder": [
                                    {
                                        "directive": "required",
                                        "field_id": [
                                            "1f44d55f-f161-4938-a659-f8026467f126"
                                        ],
                                    }
                                ],
                                "fields": [
                                    {
                                        "id": "1f44d55f-f161-4938-a659-f8026467f126",
                                        "path": ["$.credentialSubject.clearance"],
                                        "purpose": "Get clearance",  # noqa: E501
                                    },
                                ],
                            },
                        }
                    ],
                    "id": str(uuid4()),
                    "format": {"ldp_vp": {"proof_type": ["BbsBlsSignature2020"]}},
                },
                domain="building-access",
            )
        with section("Presentation summary", character="-"):
            print(presentation_summary(alice_pres_ex))


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
