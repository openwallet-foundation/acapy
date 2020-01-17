"""Utilities for dealing with indy conventions."""


from .....holder.base import BaseHolder

from ..messages.inner.presentation_preview import PresentationPreview


async def indy_proof_req_preview2indy_requested_creds(
    indy_proof_request: dict,
    preview: PresentationPreview = None,
    *,
    holder: BaseHolder
):
    """
    Build indy requested-credentials structure.

    Given input proof request and presentation preview, use credentials in
    holder's wallet to build indy requested credentials structure for input
    to proof creation.

    Args:
        indy_proof_request: indy proof request
        pres_preview: preview from presentation proposal, if applicable
        holder: holder injected into current context

    """
    req_creds = {
        "self_attested_attributes": {},
        "requested_attributes": {},
        "requested_predicates": {}
    }

    for referent in indy_proof_request["requested_attributes"]:
        credentials = (
            await holder.get_credentials_for_presentation_request_by_referent(
                presentation_request=indy_proof_request,
                referents=(referent,),
                start=0,
                count=100
            )
        )
        if not credentials:
            raise ValueError(
                f"Could not automatically construct presentation for "
                + f"presentation request {indy_proof_request['name']}"
                + f":{indy_proof_request['version']} because referent "
                + f"{referent} did not produce any credentials."
            )

        # match returned creds against any preview values
        if len(credentials) == 1:
            cred_id = credentials[0]["cred_info"]["referent"]
        else:
            if preview:
                for cred in sorted(
                    credentials,
                    key=lambda c: c["cred_info"]["referent"]
                ):
                    name = indy_proof_request["requested_attributes"][referent]["name"]
                    value = cred["cred_info"]["attrs"][name]
                    if preview.has_attr_spec(
                        cred_def_id=cred["cred_info"]["cred_def_id"],
                        name=name,
                        value=value
                    ):
                        cred_id = cred["cred_info"]["referent"]
                        break
                else:
                    raise ValueError(
                        f"Could not automatically construct presentation for "
                        + f"presentation request {indy_proof_request['name']}"
                        + f":{indy_proof_request['version']} because referent "
                        + f"{referent} did not produce any credentials matching "
                        + f"proposed preview."
                    )
            else:
                cred_id = min(cred["cred_info"]["referent"] for cred in credentials)
        req_creds["requested_attributes"][referent] = {
            "cred_id": cred_id,
            "revealed": True  # TODO allow specification of unrevealed attrs?
        }

    for referent in indy_proof_request["requested_predicates"]:
        credentials = (
            await holder.get_credentials_for_presentation_request_by_referent(
                presentation_request=indy_proof_request,
                referents=(referent,),
                start=0,
                count=100
            )
        )
        if not credentials:
            raise ValueError(
                f"Could not automatically construct presentation for "
                + f"presentation request {indy_proof_request['name']}"
                + f":{indy_proof_request['version']} because predicate "
                + f"referent {referent} did not produce any credentials."
            )

        if len(credentials) == 1:
            cred_id = credentials[0]["cred_info"]["referent"]
        else:
            cred_id = min(cred["cred_info"]["referent"] for cred in credentials)
        req_creds["requested_predicates"][referent] = {
            "cred_id": cred_id,
            "revealed": True  # TODO allow specification of unrevealed attrs?
        }

    return req_creds
