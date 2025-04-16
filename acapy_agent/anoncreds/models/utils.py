"""Utilities to deal with anoncreds objects."""

from ..holder import AnonCredsHolder


def _get_value_error_msg(proof_request: dict, referent: str) -> str:
    return (
        "Could not automatically construct presentation for "
        + f"presentation request {proof_request['name']}"
        + f":{proof_request['version']} because referent "
        + f"{referent} did not produce any credentials."
    )


async def get_requested_creds_from_proof_request_preview(
    proof_request: dict,
    *,
    holder: AnonCredsHolder,
) -> dict[str, dict]:
    """Build anoncreds requested-credentials structure.

    Given input proof request and presentation preview, use credentials in
    holder's wallet to build anoncreds requested credentials structure for input
    to proof creation.

    Args:
        proof_request: anoncreds proof request
        preview: preview from presentation proposal, if applicable
        holder: holder injected into current context

    """
    req_creds = {
        "self_attested_attributes": {},
        "requested_attributes": {},
        "requested_predicates": {},
    }

    for referent, _ in proof_request["requested_attributes"].items():
        credentials = await holder.get_credentials_for_presentation_request_by_referent(
            presentation_request=proof_request,
            referents=(referent,),
            offset=0,
            limit=100,
        )
        if not credentials:
            raise ValueError(_get_value_error_msg(proof_request, referent))

        cred_match = credentials[0]  # holder sorts

        if "restrictions" in proof_request["requested_attributes"][referent]:
            req_creds["requested_attributes"][referent] = {
                "cred_id": cred_match["cred_info"]["referent"],
                "revealed": True,
            }
        else:
            req_creds["self_attested_attributes"][referent] = cred_match["cred_info"][
                "attrs"
            ][proof_request["requested_attributes"][referent]["name"]]

    for referent in proof_request["requested_predicates"]:
        credentials = await holder.get_credentials_for_presentation_request_by_referent(
            presentation_request=proof_request,
            referents=(referent,),
            offset=0,
            limit=100,
        )
        if not credentials:
            raise ValueError(_get_value_error_msg(proof_request, referent))

        cred_match = credentials[0]  # holder sorts
        if "restrictions" in proof_request["requested_predicates"][referent]:
            req_creds["requested_predicates"][referent] = {
                "cred_id": cred_match["cred_info"]["referent"],
                "revealed": True,
            }
        else:
            req_creds["self_attested_attributes"][referent] = cred_match["cred_info"][
                "attrs"
            ][proof_request["requested_predicates"][referent]["name"]]

    return req_creds


def extract_non_revocation_intervals_from_proof_request(proof_req: dict) -> dict:
    """Return non-revocation intervals by requested item referent in proof request."""
    non_revoc_intervals = {}
    for req_item_type in ("requested_attributes", "requested_predicates"):
        for reft, req_item in proof_req[req_item_type].items():
            interval = req_item.get(
                "non_revoked",
                proof_req.get("non_revoked"),
            )
            if interval:
                timestamp_from = interval.get("from")
                timestamp_to = interval.get("to")
                if (timestamp_to is not None) and timestamp_from == timestamp_to:
                    interval["from"] = 0  # accommodate verify=False if from=to
            non_revoc_intervals[reft] = interval
    return non_revoc_intervals
