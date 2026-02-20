"""Scenario helpers for ACA-Py examples."""

import json
import time
from dataclasses import dataclass
from secrets import randbelow
from typing import Any, Dict, List, Mapping, Optional, Tuple, Type, Union
from uuid import uuid4

from acapy_controller import Controller
from acapy_controller.controller import Minimal, MinType
from acapy_controller.models import V20CredExRecordIndy, V20PresExRecord
from docker.models.containers import Container


# docker utilities:
def healthy(container: Container) -> bool:
    """Check if container is healthy."""
    inspect_results = container.attrs
    return (
        inspect_results["State"]["Running"]
        and inspect_results["State"]["Health"]["Status"] == "healthy"
    )


def unhealthy(container: Container) -> bool:
    """Check if container is unhealthy."""
    inspect_results = container.attrs
    return not inspect_results["State"]["Running"]


def wait_until_healthy(client, container_id: str, attempts: int = 350, is_healthy=True):
    """Wait until container is healthy."""
    container = client.containers.get(container_id)
    print((container.name, container.status))
    for _ in range(attempts):
        if (is_healthy and healthy(container)) or unhealthy(container):
            return
        else:
            time.sleep(1)
        container = client.containers.get(container_id)
    raise TimeoutError("Timed out waiting for container")


def update_wallet_type(agent_command: List, wallet_type: str) -> str:
    """Update the wallet type argument in a CLI command list."""
    for i in range(len(agent_command) - 1):
        if agent_command[i] == "--wallet-type":
            agent_command[i + 1] = wallet_type
            return wallet_type
    raise Exception("Error unable to upgrade wallet type to askar-anoncreds")


def get_wallet_name(agent_command: List) -> str:
    """Return the wallet name argument from a CLI command list."""
    for i in range(len(agent_command) - 1):
        if agent_command[i] == "--wallet-name":
            return agent_command[i + 1]
    raise Exception("Error unable to upgrade wallet type to askar-anoncreds")


def _presentation_request_payload(
    presentation: V20PresExRecord,
) -> Optional[Dict[str, Any]]:
    if presentation.by_format and presentation.by_format.pres_request:
        return presentation.by_format.pres_request
    request = presentation.pres_request
    if not request:
        return None
    if isinstance(request, dict):
        return request
    if hasattr(request, "model_dump"):
        return request.model_dump(by_alias=True)
    return request.dict(by_alias=True)


# anoncreds utilities:
def anoncreds_presentation_summary(presentation: V20PresExRecord) -> str:
    """Summarize a presentation exchange record."""
    request = _presentation_request_payload(presentation)
    return "Summary: " + json.dumps(
        {
            "state": presentation.state,
            "verified": presentation.verified,
            "presentation_request": request,
        },
        indent=2,
        sort_keys=True,
    )


@dataclass
class SchemaResultAnonCreds(Minimal):
    """Schema result."""

    schema_state: dict


@dataclass
class CredDefResultAnonCreds(Minimal):
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
class V20CredExRecordFormat(Minimal):
    """V2.0 credential exchange record anoncreds."""

    rev_reg_id: Optional[str] = None
    cred_rev_id: Optional[str] = None


@dataclass
class V20CredExRecordDetail(Minimal):
    """V2.0 credential exchange record detail."""

    cred_ex_record: V20CredExRecord
    details: Optional[V20CredExRecordFormat] = None


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


@dataclass
class Settings(Minimal):
    """Settings information."""


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


async def indy_present_proof_v2(
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
    cred_rev_id: Optional[str] = None,
):
    """Present a credential using present proof v2 (indy).

    This follows the acapy_controller.protocols flow, but resolves the holder-side
    request payload via _presentation_request_payload(...) to support both legacy
    pres_request and by_format webhook payload shapes.
    """
    attrs = {
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
    }

    verifier_pres_ex = await verifier.post(
        "/present-proof-2.0/send-request",
        json={
            "auto_verify": False,
            "comment": comment or "Presentation request from minimal",
            "connection_id": verifier_connection_id,
            "presentation_request": {"indy": attrs},
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
    holder_pres_ex_id = holder_pres_ex.pres_ex_id

    relevant_creds = await holder.get(
        f"/present-proof-2.0/records/{holder_pres_ex_id}/credentials",
        response=List[CredPrecis],
    )

    if cred_rev_id:
        relevant_creds = [
            cred
            for cred in relevant_creds
            if cred.cred_info._extra.get("cred_rev_id") == cred_rev_id
        ]

    request_payload = _presentation_request_payload(holder_pres_ex)
    assert request_payload
    proof_request = request_payload
    if "anoncreds" in request_payload or "indy" in request_payload:
        proof_request = request_payload.get("indy") or request_payload.get("anoncreds")
        assert proof_request
    pres_spec = auto_select_credentials_for_presentation_request(
        proof_request, relevant_creds
    )
    await holder.post(
        f"/present-proof-2.0/records/{holder_pres_ex_id}/send-presentation",
        json={"indy": pres_spec.serialize()},
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


async def jsonld_present_proof_v2(
    holder: Controller,
    verifier: Controller,
    holder_connection_id: str,
    verifier_connection_id: str,
    *,
    presentation_definition: Mapping[str, Any],
    domain: Optional[str] = None,
    challenge: Optional[str] = None,
    comment: Optional[str] = None,
):
    """Present a credential using present proof v2 (DIF/JSON-LD)."""
    dif_options: Dict[str, Any] = {"challenge": challenge or str(uuid4())}
    if domain:
        dif_options["domain"] = domain

    verifier_pres_ex = await verifier.post(
        "/present-proof-2.0/send-request",
        json={
            "auto_verify": False,
            "comment": comment or "Presentation request from minimal",
            "connection_id": verifier_connection_id,
            "presentation_request": {
                "dif": {
                    "presentation_definition": dict(presentation_definition),
                    "options": dif_options,
                }
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
    holder_pres_ex_id = holder_pres_ex.pres_ex_id

    await holder.post(
        f"/present-proof-2.0/records/{holder_pres_ex_id}/send-presentation",
        json={"dif": {}},
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


async def anoncreds_issue_credential_v2(
    issuer: Controller,
    holder: Controller,
    issuer_connection_id: str,
    holder_connection_id: str,
    attributes: Mapping[str, str],
    cred_def_id: str,
    issuer_id: Optional[str] = None,
    schema_id: Optional[str] = None,
    schema_issuer_id: Optional[str] = None,
    schema_name: Optional[str] = None,
    schema_version: Optional[str] = None,
) -> Tuple[V20CredExRecordDetail, V20CredExRecordDetail]:
    """Issue an credential using issue-credential/2.0.

    Issuer and holder should already be connected.
    """
    issuer_wallet_type = (await issuer.get("/settings", response=Settings)).get(
        "wallet.type"
    )
    holder_wallet_type = (await holder.get("/settings", response=Settings)).get(
        "wallet.type"
    )

    is_issuer_anoncreds = issuer_wallet_type in (
        "askar-anoncreds",
        "kanon-anoncreds",
    )
    is_holder_anoncreds = holder_wallet_type in (
        "askar-anoncreds",
        "kanon-anoncreds",
    )

    if is_issuer_anoncreds:
        _filter = {"anoncreds": {"cred_def_id": cred_def_id}}
        if issuer_id:
            _filter["anoncreds"]["issuer_id"] = issuer_id
        if schema_id:
            _filter["anoncreds"]["schema_id"] = schema_id
        if schema_issuer_id:
            _filter["anoncreds"]["schema_issuer_id"] = schema_issuer_id
        if schema_name:
            _filter["anoncreds"]["schema_name"] = schema_name
        if schema_version:
            _filter["anoncreds"]["schema_version"] = schema_version

    else:
        _filter = {"indy": {"cred_def_id": cred_def_id}}
        if issuer_id:
            _filter["indy"]["issuer_did"] = issuer_id
        if schema_id:
            _filter["indy"]["schema_id"] = schema_id
        if schema_issuer_id:
            _filter["indy"]["schema_issuer_did"] = schema_issuer_id
        if schema_name:
            _filter["indy"]["schema_name"] = schema_name
        if schema_version:
            _filter["indy"]["schema_version"] = schema_version

    issuer_cred_ex = await issuer.post(
        "/issue-credential-2.0/send-offer",
        json={
            "auto_issue": False,
            "auto_remove": False,
            "comment": "Credential from minimal example",
            "trace": False,
            "connection_id": issuer_connection_id,
            "filter": _filter,
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
    issuer_indy_record = await issuer.event_with_values(
        topic=(
            "issue_credential_v2_0_anoncreds"
            if is_issuer_anoncreds
            else "issue_credential_v2_0_indy"
        ),
        event_type=V20CredExRecordIndy,
    )

    holder_cred_ex = await holder.event_with_values(
        topic="issue_credential_v2_0",
        event_type=V20CredExRecord,
        cred_ex_id=holder_cred_ex_id,
        state="done",
    )
    holder_indy_record = await holder.event_with_values(
        topic=(
            "issue_credential_v2_0_anoncreds"
            if (is_holder_anoncreds or is_issuer_anoncreds)
            else "issue_credential_v2_0_indy"
        ),
        event_type=V20CredExRecordIndy,
    )

    return (
        V20CredExRecordDetail(cred_ex_record=issuer_cred_ex, details=issuer_indy_record),
        V20CredExRecordDetail(
            cred_ex_record=holder_cred_ex,
            details=holder_indy_record,
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
    cred_rev_id: Optional[str] = None,
):
    """Present an credential using present proof v2."""
    verifier_wallet_type = (await verifier.get("/settings", response=Settings)).get(
        "wallet.type"
    )
    is_verifier_anoncreds = verifier_wallet_type in (
        "askar-anoncreds",
        "kanon-anoncreds",
    )

    attrs = {
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
    }

    if is_verifier_anoncreds:
        presentation_request = {
            "anoncreds": attrs,
        }
    else:
        presentation_request = {
            "indy": attrs,
        }
    verifier_pres_ex = await verifier.post(
        "/present-proof-2.0/send-request",
        json={
            "auto_verify": False,
            "comment": comment or "Presentation request from minimal",
            "connection_id": verifier_connection_id,
            "presentation_request": presentation_request,
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
    holder_pres_ex_id = holder_pres_ex.pres_ex_id

    relevant_creds = await holder.get(
        f"/present-proof-2.0/records/{holder_pres_ex_id}/credentials",
        response=List[CredPrecis],
    )

    # Filter credentials by revocation id to allow selecting non-revoked
    if cred_rev_id:
        relevant_creds = [
            cred
            for cred in relevant_creds
            if cred.cred_info._extra.get("cred_rev_id") == cred_rev_id
        ]

    request_payload = _presentation_request_payload(holder_pres_ex)
    assert request_payload
    proof_request = request_payload
    if "anoncreds" in request_payload or "indy" in request_payload:
        proof_request = request_payload.get("anoncreds") or request_payload.get("indy")
        assert proof_request
    pres_spec = auto_select_credentials_for_presentation_request(
        proof_request, relevant_creds
    )
    if is_verifier_anoncreds:
        proof = {"anoncreds": pres_spec.serialize()}
    else:
        proof = {"indy": pres_spec.serialize()}
    await holder.post(
        f"/present-proof-2.0/records/{holder_pres_ex_id}/send-presentation",
        json=proof,
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
