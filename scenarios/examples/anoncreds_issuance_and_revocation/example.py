"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from datetime import datetime
from os import getenv
from secrets import token_hex

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.models import (
    CreateWalletResponse,
)
from acapy_controller.protocols import (
    DIDResult,
    didexchange,
    indy_anoncred_credential_artifacts,
    params,
)
from aiohttp import ClientSession
from examples.util import (
    CredDefResultAnoncreds,
    SchemaResultAnoncreds,
    anoncreds_issue_credential_v2,
    anoncreds_present_proof_v2,
)

AGENCY = getenv("AGENCY", "http://agency:3001")
HOLDER_ANONCREDS = getenv("HOLDER_ANONCREDS", "http://holder_anoncreds:3001")
HOLDER_INDY = getenv("HOLDER_INDY", "http://holder_indy:3001")


async def main():
    """Test Controller protocols."""
    issuer_name = "issuer" + token_hex(8)
    issuer_without_schema_name = "issuer" + token_hex(8)
    async with Controller(base_url=AGENCY) as agency:
        issuer = await agency.post(
            "/multitenancy/wallet",
            json={
                "label": issuer_name,
                "wallet_name": issuer_name,
                "wallet_type": "askar",
            },
            response=CreateWalletResponse,
        )
        issuer_without_schema = await agency.post(
            "/multitenancy/wallet",
            json={
                "label": issuer_without_schema_name,
                "wallet_name": issuer_without_schema_name,
                "wallet_type": "askar",
            },
            response=CreateWalletResponse,
        )

    async with (
        Controller(
            base_url=AGENCY,
            wallet_id=issuer.wallet_id,
            subwallet_token=issuer.token,
        ) as issuer,
        Controller(
            base_url=AGENCY,
            wallet_id=issuer_without_schema.wallet_id,
            subwallet_token=issuer_without_schema.token,
        ) as issuer_without_schema,
        Controller(base_url=HOLDER_ANONCREDS) as holder_anoncreds,
        Controller(base_url=HOLDER_INDY) as holder_indy,
    ):
        """
            This section of the test script demonstrates the issuance, presentation and 
            revocation of a credential where both the issuer is not anoncreds capable 
            (wallet type askar) and the holder is anoncreds capable 
            (wallet type askar-anoncreds).
        """

        # Connecting
        issuer_conn_with_anoncreds_holder, holder_anoncreds_conn = await didexchange(
            issuer, holder_anoncreds
        )

        # Issuance prep
        config = (await issuer.get("/status/config"))["config"]
        genesis_url = config.get("ledger.genesis_url")
        public_did = (await issuer.get("/wallet/did/public", response=DIDResult)).result
        if not public_did:
            public_did = (
                await issuer.post(
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

            await issuer.post("/wallet/did/public", params=params(did=public_did.did))

        schema_name = "anoncreds-test-" + token_hex(8)
        schema_version = "1.0"
        schema, cred_def = await indy_anoncred_credential_artifacts(
            issuer,
            ["firstname", "lastname"],
            support_revocation=True,
            schema_name=schema_name,
            schema_version=schema_version,
        )

        # Issue a credential
        issuer_cred_ex, _ = await anoncreds_issue_credential_v2(
            issuer,
            holder_anoncreds,
            issuer_conn_with_anoncreds_holder.connection_id,
            holder_anoncreds_conn.connection_id,
            {"firstname": "Anoncreds", "lastname": "Holder"},
            cred_def_id=cred_def.credential_definition_id,
            issuer_id=public_did.did,
            schema_id=schema.schema_id,
            schema_issuer_id=public_did.did,
            schema_name=schema_name,
        )

        # Present the the credential's attributes
        _, verifier_ex = await anoncreds_present_proof_v2(
            holder_anoncreds,
            issuer,
            holder_anoncreds_conn.connection_id,
            issuer_conn_with_anoncreds_holder.connection_id,
            requested_attributes=[{"name": "firstname"}],
            non_revoked={"to": int(datetime.now().timestamp())},
            cred_rev_id=issuer_cred_ex.details.cred_rev_id,
        )
        assert verifier_ex.verified == "true"

        # Revoke credential
        await issuer.post(
            url="/revocation/revoke",
            json={
                "connection_id": issuer_conn_with_anoncreds_holder.connection_id,
                "rev_reg_id": issuer_cred_ex.details.rev_reg_id,
                "cred_rev_id": issuer_cred_ex.details.cred_rev_id,
                "publish": True,
                "notify": True,
                "notify_version": "v1_0",
            },
        )

        await holder_anoncreds.record(topic="revocation-notification")

        # Present the the credential's attributes
        now = int(datetime.now().timestamp())
        _, verifier_ex = await anoncreds_present_proof_v2(
            holder_anoncreds,
            issuer,
            holder_anoncreds_conn.connection_id,
            issuer_conn_with_anoncreds_holder.connection_id,
            requested_attributes=[{"name": "firstname"}],
            non_revoked={"to": now},
            cred_rev_id=issuer_cred_ex.details.cred_rev_id,
        )
        assert verifier_ex.verified == "false"

        # Issue another credential
        issuer_cred_ex, _ = await anoncreds_issue_credential_v2(
            issuer,
            holder_anoncreds,
            issuer_conn_with_anoncreds_holder.connection_id,
            holder_anoncreds_conn.connection_id,
            {"firstname": "Anoncreds", "lastname": "Holder"},
            cred_def_id=cred_def.credential_definition_id,
            issuer_id=public_did.did,
            schema_id=schema.schema_id,
            schema_issuer_id=public_did.did,
            schema_name=schema_name,
        )

        valid_anoncreds_holder_cred_rev_id = issuer_cred_ex.details.cred_rev_id

        # Holder has one revoked and one non-revoked credential
        _, verifier_ex = await anoncreds_present_proof_v2(
            holder_anoncreds,
            issuer,
            holder_anoncreds_conn.connection_id,
            issuer_conn_with_anoncreds_holder.connection_id,
            requested_attributes=[{"name": "firstname"}],
            non_revoked={"to": now},
            cred_rev_id=issuer_cred_ex.details.cred_rev_id,
        )
        assert verifier_ex.verified == "true"

        """
            This section of the test script demonstrates the issuance, presentation and
            revocation of a credential where the issuer and holder are not anoncreds
            capable. Both are askar wallet type.
        """

        # Connecting
        issuer_conn_with_indy_holder, holder_indy_conn = await didexchange(
            issuer, holder_indy
        )

        # Issue a credential
        issuer_cred_ex, _ = await anoncreds_issue_credential_v2(
            issuer,
            holder_indy,
            issuer_conn_with_indy_holder.connection_id,
            holder_indy_conn.connection_id,
            {"firstname": "Indy", "lastname": "Holder"},
            cred_def_id=cred_def.credential_definition_id,
            issuer_id=public_did.did,
            schema_id=schema.schema_id,
            schema_issuer_id=public_did.did,
            schema_name=schema_name,
        )

        # Present the the credential's attributes
        _, verifier_ex = await anoncreds_present_proof_v2(
            holder_indy,
            issuer,
            holder_indy_conn.connection_id,
            issuer_conn_with_indy_holder.connection_id,
            requested_attributes=[{"name": "firstname"}],
            non_revoked={"to": int(datetime.now().timestamp())},
            cred_rev_id=issuer_cred_ex.details.cred_rev_id,
        )
        assert verifier_ex.verified == "true"

        # Revoke credential
        await issuer.post(
            url="/revocation/revoke",
            json={
                "connection_id": issuer_conn_with_indy_holder.connection_id,
                "rev_reg_id": issuer_cred_ex.details.rev_reg_id,
                "cred_rev_id": issuer_cred_ex.details.cred_rev_id,
                "publish": True,
                "notify": True,
                "notify_version": "v1_0",
            },
        )

        await holder_indy.record(topic="revocation-notification")

        # Presentation after revocation should fail
        now = int(datetime.now().timestamp())
        _, verifier_ex = await anoncreds_present_proof_v2(
            holder_indy,
            issuer,
            holder_indy_conn.connection_id,
            issuer_conn_with_indy_holder.connection_id,
            requested_attributes=[{"name": "firstname"}],
            non_revoked={"to": now},
            cred_rev_id=issuer_cred_ex.details.cred_rev_id,
        )
        assert verifier_ex.verified == "false"

        # Add another credential to the holder and present it
        issuer_cred_ex, _ = await anoncreds_issue_credential_v2(
            issuer,
            holder_indy,
            issuer_conn_with_indy_holder.connection_id,
            holder_indy_conn.connection_id,
            {"firstname": "Indy", "lastname": "Holder"},
            cred_def_id=cred_def.credential_definition_id,
            issuer_id=public_did.did,
            schema_id=schema.schema_id,
            schema_issuer_id=public_did.did,
            schema_name=schema_name,
        )

        valid_indy_holder_cred_rev_id = issuer_cred_ex.details.cred_rev_id

        # Presentation with one revoked and one valid credential
        _, verifier_ex = await anoncreds_present_proof_v2(
            holder_indy,
            issuer,
            holder_indy_conn.connection_id,
            issuer_conn_with_indy_holder.connection_id,
            requested_attributes=[{"name": "firstname"}],
            non_revoked={"to": now},
            cred_rev_id=issuer_cred_ex.details.cred_rev_id,
        )
        assert verifier_ex.verified == "true"

        """
            Upgrade the issuer tenant to anoncreds capable wallet type. When upgrading a
            tenant the agent doesn't require a restart. That is why the test is done
            with multitenancy
        """
        await issuer.post(
            "/anoncreds/wallet/upgrade",
            params={
                "wallet_name": issuer_name,
            },
        )
        # Wait for the upgrade to complete
        await asyncio.sleep(1)

        await issuer_without_schema.post(
            "/anoncreds/wallet/upgrade",
            params={
                "wallet_name": issuer_without_schema_name,
            },
        )
        # Wait for the upgrade to complete
        await asyncio.sleep(1)

        """
            Do issuance and presentation again after the upgrade. This time the issuer is
            an anoncreds capable wallet (wallet type askar-anoncreds).
        """
        # Presentation for anoncreds capable holder on existing credential
        _, verifier_ex = await anoncreds_present_proof_v2(
            holder_anoncreds,
            issuer,
            holder_anoncreds_conn.connection_id,
            issuer_conn_with_anoncreds_holder.connection_id,
            requested_attributes=[{"name": "firstname"}],
            non_revoked={"to": now},
            cred_rev_id=valid_anoncreds_holder_cred_rev_id,
        )
        assert verifier_ex.verified == "true"

        # Presentation for indy capable holder on existing credential
        _, verifier_ex = await anoncreds_present_proof_v2(
            holder_indy,
            issuer,
            holder_indy_conn.connection_id,
            issuer_conn_with_indy_holder.connection_id,
            requested_attributes=[{"name": "firstname"}],
            non_revoked={"to": now},
            cred_rev_id=valid_indy_holder_cred_rev_id,
        )
        assert verifier_ex.verified == "true"

        # Create a new schema and cred def with different attributes on new
        # anoncreds endpoints
        schema_name = "anoncreds-test-" + token_hex(8)
        schema_version = "1.0"
        schema = await issuer.post(
            "/anoncreds/schema",
            json={
                "schema": {
                    "name": schema_name,
                    "version": schema_version,
                    "attrNames": ["middlename"],
                    "issuerId": public_did.did,
                }
            },
            response=SchemaResultAnoncreds,
        )
        cred_def = await issuer.post(
            "/anoncreds/credential-definition",
            json={
                "credential_definition": {
                    "issuerId": schema.schema_state["schema"]["issuerId"],
                    "schemaId": schema.schema_state["schema_id"],
                    "tag": token_hex(8),
                },
                "options": {"support_revocation": True, "revocation_registry_size": 10},
            },
            response=CredDefResultAnoncreds,
        )

        # Issue a new credential to anoncreds holder
        issuer_cred_ex, _ = await anoncreds_issue_credential_v2(
            issuer,
            holder_anoncreds,
            issuer_conn_with_anoncreds_holder.connection_id,
            holder_anoncreds_conn.connection_id,
            {"middlename": "Anoncreds"},
            cred_def_id=cred_def.credential_definition_state["credential_definition_id"],
            issuer_id=public_did.did,
            schema_id=schema.schema_state["schema_id"],
            schema_issuer_id=public_did.did,
            schema_name=schema_name,
        )
        # Presentation for anoncreds capable holder
        _, verifier_ex = await anoncreds_present_proof_v2(
            holder_anoncreds,
            issuer,
            holder_anoncreds_conn.connection_id,
            issuer_conn_with_anoncreds_holder.connection_id,
            requested_attributes=[{"name": "middlename"}],
            non_revoked={"to": int(datetime.now().timestamp())},
            cred_rev_id=issuer_cred_ex.details.cred_rev_id,
        )
        assert verifier_ex.verified == "true"
        # Revoke credential
        await issuer.post(
            url="/anoncreds/revocation/revoke",
            json={
                "connection_id": issuer_conn_with_anoncreds_holder.connection_id,
                "rev_reg_id": issuer_cred_ex.details.rev_reg_id,
                "cred_rev_id": issuer_cred_ex.details.cred_rev_id,
                "publish": True,
                "notify": True,
                "notify_version": "v1_0",
            },
        )
        await holder_anoncreds.record(topic="revocation-notification")

        _, verifier_ex = await anoncreds_present_proof_v2(
            holder_anoncreds,
            issuer,
            holder_anoncreds_conn.connection_id,
            issuer_conn_with_anoncreds_holder.connection_id,
            requested_attributes=[{"name": "middlename"}],
            non_revoked={"to": int(datetime.now().timestamp())},
            cred_rev_id=issuer_cred_ex.details.cred_rev_id,
        )
        assert verifier_ex.verified == "false"

        # Issue a new credential to indy holder
        issuer_cred_ex, _ = await anoncreds_issue_credential_v2(
            issuer,
            holder_indy,
            issuer_conn_with_indy_holder.connection_id,
            holder_indy_conn.connection_id,
            {"middlename": "Indy"},
            cred_def_id=cred_def.credential_definition_state["credential_definition_id"],
            issuer_id=public_did.did,
            schema_id=schema.schema_state["schema_id"],
            schema_issuer_id=public_did.did,
            schema_name=schema_name,
        )
        # Presentation for indy holder
        _, verifier_ex = await anoncreds_present_proof_v2(
            holder_indy,
            issuer,
            holder_indy_conn.connection_id,
            issuer_conn_with_indy_holder.connection_id,
            requested_attributes=[{"name": "middlename"}],
            non_revoked={"to": int(datetime.now().timestamp())},
            cred_rev_id=issuer_cred_ex.details.cred_rev_id,
        )
        assert verifier_ex.verified == "true"
        # Revoke credential
        await issuer.post(
            url="/anoncreds/revocation/revoke",
            json={
                "connection_id": issuer_conn_with_indy_holder.connection_id,
                "rev_reg_id": issuer_cred_ex.details.rev_reg_id,
                "cred_rev_id": issuer_cred_ex.details.cred_rev_id,
                "publish": True,
                "notify": True,
                "notify_version": "v1_0",
            },
        )

        await holder_indy.record(topic="revocation-notification")

        _, verifier_ex = await anoncreds_present_proof_v2(
            holder_indy,
            issuer,
            holder_indy_conn.connection_id,
            issuer_conn_with_indy_holder.connection_id,
            requested_attributes=[{"name": "middlename"}],
            non_revoked={"to": int(datetime.now().timestamp())},
            cred_rev_id=issuer_cred_ex.details.cred_rev_id,
        )
        assert verifier_ex.verified == "false"

        """
            This section of the test script demonstrates the issuance, presentation and
            revocation of a credential where the issuer did not create the schema.
        """
        print(
            "***Begin issuance, presentation and revocation of "
            "credential without schema***"
        )
        issuer_conn_with_anoncreds_holder, holder_anoncreds_conn = await didexchange(
            issuer_without_schema, holder_anoncreds
        )

        public_did = (
            await issuer_without_schema.post(
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

        await issuer_without_schema.post(
            "/wallet/did/public", params=params(did=public_did.did)
        )
        cred_def = await issuer_without_schema.post(
            "/anoncreds/credential-definition",
            json={
                "credential_definition": {
                    "issuerId": public_did.did,
                    "schemaId": schema.schema_state["schema_id"],
                    "tag": token_hex(8),
                },
                "options": {"support_revocation": True, "revocation_registry_size": 10},
            },
            response=CredDefResultAnoncreds,
        )
        issuer_cred_ex, _ = await anoncreds_issue_credential_v2(
            issuer_without_schema,
            holder_anoncreds,
            issuer_conn_with_anoncreds_holder.connection_id,
            holder_anoncreds_conn.connection_id,
            {"middlename": "Anoncreds"},
            cred_def_id=cred_def.credential_definition_state["credential_definition_id"],
            schema_id=schema.schema_state["schema_id"],
        )
        await anoncreds_present_proof_v2(
            holder_anoncreds,
            issuer_without_schema,
            holder_anoncreds_conn.connection_id,
            issuer_conn_with_anoncreds_holder.connection_id,
            requested_attributes=[{"name": "middlename"}],
        )
        await issuer_without_schema.post(
            url="/anoncreds/revocation/revoke",
            json={
                "connection_id": issuer_conn_with_anoncreds_holder.connection_id,
                "rev_reg_id": issuer_cred_ex.details.rev_reg_id,
                "cred_rev_id": issuer_cred_ex.details.cred_rev_id,
                "publish": True,
                "notify": True,
                "notify_version": "v1_0",
            },
        )

        await holder_anoncreds.record(topic="revocation-notification")


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
