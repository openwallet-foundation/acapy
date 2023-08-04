"""
Copyright 2017-2019 Government of Canada
Public Services and Procurement Canada - buyandsell.gc.ca

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from .. import LegacyDIDDoc, PublicKey, PublicKeyType, Service
from ..util import canon_did, canon_ref


class TestLegacyDIDDoc(AsyncTestCase):
    def test_acapy_didx_example(self):
        # payload produced in simple 0.9 example
        dd_in = {
            "@context": [
                "https://www.w3.org/ns/did/v1"
            ],
            "id": "did:sov:2nWv86UP1q4HRhdjCWQwzn",
            "publicKey": [
                {
                "id": "did:sov:2nWv86UP1q4HRhdjCWQwzn#1",
                "type": "Ed25519VerificationKey2018",
                "controller": "did:sov:2nWv86UP1q4HRhdjCWQwzn",
                "publicKeyBase58": "yRLcpx1EMGEy9bZqmTefzsT5BrwokHmcodstCDjQWnK"
                }
            ],
            "authentication": [
                {
                "type": "Ed25519SignatureAuthentication2018",
                "publicKey": "did:sov:2nWv86UP1q4HRhdjCWQwzn#1"
                }
            ],
            "service": [
                {
                "id": "did:sov:2nWv86UP1q4HRhdjCWQwzn;indy",
                "type": "IndyAgent",
                "priority": 0,
                "recipientKeys": [
                    "yRLcpx1EMGEy9bZqmTefzsT5BrwokHmcodstCDjQWnK"
                ],
                "serviceEndpoint": "http://host.docker.internal:8020"
                }
            ]
        }


        dd =LegacyDIDDoc.deserialize(dd_in)

        # print('\n\n== 4 == DID Doc on mixed reference styles, embedded and ref style authn keys: {}'.format(ppjson(dd_out)))


    async def test_obsolete_basic(self):
        # One authn key by reference
        dd_in = {
            "@context": "https://w3id.org/did/v1",
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "publicKey": [
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#3",
                    "type": "RsaVerificationKey2018",
                    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyPem": "-----BEGIN PUBLIC X...",
                },
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#4",
                    "type": "RsaVerificationKey2018",
                    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyPem": "-----BEGIN PUBLIC 9...",
                },
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#6",
                    "type": "RsaVerificationKey2018",
                    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyPem": "-----BEGIN PUBLIC A...",
                },
            ],
            "authentication": [
                {
                    "type": "RsaSignatureAuthentication2018",
                    "publicKey": "did:sov:LjgpST2rjsoxYegQDRm7EL#4",
                }
            ],
            "service": [
                {
                    "id": "#0",
                    "type": "DIDCommMessaging",
                    "serviceEndpoint": "http://host.docker.internal:9070",
                    "recipient_keys":[]
                }
            ],
        }

        dd = LegacyDIDDoc.deserialize(dd_in)
        
        assert len(dd.verification_method) == len(dd_in["publicKey"]) + len(dd_in["authentication"])
        assert len(dd.service) == 1

    def test_obsolete_reference_authkey(self):
        # All references canonical where possible; one authn key embedded and one by reference
        dd_in = {
            "@context": "https://w3id.org/did/v1",
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "publicKey": [
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#3",
                    "type": "RsaVerificationKey2018",
                    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyPem": "-----BEGIN PUBLIC X...",
                },
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#4",
                    "type": "RsaVerificationKey2018",
                    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyPem": "-----BEGIN PUBLIC 9...",
                },
            ],
            "authentication": [
                {
                    "type": "RsaSignatureAuthentication2018",
                    "publicKey": "did:sov:LjgpST2rjsoxYegQDRm7EL#4",
                },
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#6",
                    "type": "RsaVerificationKey2018",
                    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyPem": "-----BEGIN PUBLIC A...",
                },
            ],
            "service": [
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL;0",
                    "type": "DIDCommMessaging",
                    "serviceEndpoint": "https://www.von.ca",
                }
            ],
        }

        dd =LegacyDIDDoc.deserialize(dd_in)
        assert len(dd.verification_method) == len(dd_in["publicKey"]) + len(dd_in["authentication"])

        dd_out = dd.serialize()
        # print('\n\n== 5 == DID Doc on canonical refs: {}'.format(ppjson(dd_out)))


    def test_obsolete_minimal_ids(self):
        # Minimal + ids as per indy-agent test suite with explicit identifiers; novel service recipient key on raw base58
        dd_in = {
            "@context": "https://w3id.org/did/v1",
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "publicKey": [
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-1",
                    "type": "Ed25519VerificationKey2018",
                    "controller": "did:sov:",
                    "publicKeyBase58": "~XXXXXXXXXXXXXXXX",
                }
            ],
            "service": [
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL;indy",
                    "type": "DIDCommMessaging",
                    "priority": 1,
                    "recipientKeys": ["~YYYYYYYYYYYYYYYY"],
                    "serviceEndpoint": "https://www.von.ca",
                }
            ],
        }

        dd =LegacyDIDDoc.deserialize(dd_in)
        assert len(dd.verification_method) == 1 + len(dd_in["publicKey"])

        dd_out = dd.serialize()
        # print('\n\n== 7 == DID Doc miminal style plus explicit idents and novel raw base58 service recip key: {}'.format(
        #    ppjson(dd_out)))

    def test_obsolete_minimal_explicit(self):
        # Minimal + ids as per indy-agent test suite with explicit identifiers; novel service recipient key on raw base58
        dd_in = {
            "@context": "https://w3id.org/did/v1",
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "publicKey": [
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-1",
                    "type": "Ed25519VerificationKey2018",
                    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyBase58": "~XXXXXXXXXXXXXXXX",
                },
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-2",
                    "type": "Ed25519VerificationKey2018",
                    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyBase58": "~YYYYYYYYYYYYYYYY",
                },
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-3",
                    "type": "Secp256k1VerificationKey2018",
                    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyHex": "02b97c30de767f084ce3080168ee293053ba33b235d7116a3263d29f1450936b71",
                },
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4",
                    "type": "RsaVerificationKey2018",
                    "controller": "did:sov:did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyPem": "-----BEGIN PUBLIC A...",
                },
            ],
            "service": [
                {
                    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL;indy",
                    "type": "DIDCommMessaging",
                    "priority": 0,
                    "recipientKeys": ["~ZZZZZZZZZZZZZZZZ"],
                    "serviceEndpoint": "did:sov:LjgpST2rjsoxYegQDRm7EL;1",
                },
                {
                    "id": "1",
                    "type": "DIDCommMessaging",
                    "priority": 1,
                    "recipientKeys": [
                        "~XXXXXXXXXXXXXXXX",
                        "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-1",
                    ],
                    "routingKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4"],
                    "serviceEndpoint": "did:sov:LjgpST2rjsoxYegQDRm7EL;2",
                },
                {
                    "id": "2",
                    "type": "DIDCommMessaging",
                    "priority": 2,
                    "recipientKeys": [
                        "~XXXXXXXXXXXXXXXX",
                        "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-1",
                    ],
                    "routingKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4"],
                    "serviceEndpoint": "https://www.two.ca/two",
                },
            ],
        }

        dd =LegacyDIDDoc.deserialize(dd_in)
        assert len(dd.verification_method) == len(dd_in["publicKey"])
        assert {s.priority for s in dd.service} == {0, 1, 2}
        assert len(dd.service) == 3
        assert all(
            len(k.dict()["recipient_keys"]) == 1 for k in dd.service
        )
        # id - did:sov:LjgpST2rjsoxYegQDRm7EL;indy -> #indy
        assert (
            "routingKeys"
            not in [s for s in dd.service if s.id=="#indy"][0].dict()
        )
        assert all(
            (len(k.dict()["routing_keys"]) == 1 and k.dict()["routing_keys"][0] == "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4") for k in dd.service if k.id != "#indy"
        )


    def test_obsolete_missing_recipkey(self):
        # Exercise missing service recipient key
        dd_in = {
            "@context": "https://w3id.org/did/v1",
            "id": "LjgpST2rjsoxYegQDRm7EL",
            "publicKey": [
                {
                    "id": "LjgpST2rjsoxYegQDRm7EL#keys-1",
                    "type": "Ed25519VerificationKey2018",
                    "controller": "LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyBase58": "~XXXXXXXXXXXXXXXX",
                }
            ],
            "service": [
                {
                    "id": "LjgpST2rjsoxYegQDRm7EL;indy",
                    "type": "IndyAgent",
                    "priority": 1,
                    "recipientKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-3"],
                    "serviceEndpoint": "https://www.von.ca",
                }
            ],
        }

        with self.assertRaises(ValueError):
            dd =LegacyDIDDoc.deserialize(dd_in)
        # print('\n\n== 10 == DID Doc on underspecified service key fails as expected')

    def test_obsolete_w3c_minimal(self):
        # Minimal as per W3C Example 2, draft 0.12
        dd_in = {
            "@context": "https://w3id.org/did/v1",
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "authentication": [
                {
                    "id": "LjgpST2rjsoxYegQDRm7EL#keys-1",
                    "type": "Ed25519VerificationKey2018",
                    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyBase58": "~XXXXXXXXXXXXXXXX",
                }
            ],
            "service": [
                {
                    "type": "IndyAgent",
                    "serviceEndpoint": "https://example.com/endpoint/8377464",
                }
            ],
        }

        dd =LegacyDIDDoc.deserialize(dd_in)
        assert len(dd.verification_method) == 1
        assert len(dd.authentication) == 1
        assert len(dd.service) == 1

        dd_out = dd.serialize()
        # print('\n\n== 11 == Minimal DID Doc (no pubkey except authentication) as per W3C spec parses OK: {}'.format(
        #    ppjson(dd_out)))

    def test_obsolete_no_ident(self):
        # Exercise no-identifier case
        dd_in = {
            "@context": "https://w3id.org/did/v1",
            "authentication": [
                {
                    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "publicKeyBase58": "~XXXXXXXXXXXXXXXX",
                }
            ],
            "service": [
                {
                    "type": "DIDCommMessaging",
                    "serviceEndpoint": "https://example.com/endpoint/8377464",
                }
            ],
        }

        with self.assertRaises(ValueError):
            dd =LegacyDIDDoc.deserialize(dd_in)
        # print('\n\n== 12 == DID Doc without identifier rejected as expected')
