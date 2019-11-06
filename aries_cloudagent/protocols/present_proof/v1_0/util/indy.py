"""Utilities for dealing with indy conventions."""

from collections import namedtuple
from enum import Enum
from typing import Any

from .....holder.base import BaseHolder


Relation = namedtuple("Relation", "fortran wql math yes no")


class Predicate(Enum):
    """Enum for predicate types that indy-sdk supports."""

    LT = Relation(
        'LT',
        '$lt',
        '<',
        lambda x, y: Predicate.to_int(x) < Predicate.to_int(y),
        lambda x, y: Predicate.to_int(x) >= Predicate.to_int(y))
    LE = Relation(
        'LE',
        '$lte',
        '<=',
        lambda x, y: Predicate.to_int(x) <= Predicate.to_int(y),
        lambda x, y: Predicate.to_int(x) > Predicate.to_int(y))
    GE = Relation(
        'GE',
        '$gte',
        '>=',
        lambda x, y: Predicate.to_int(x) >= Predicate.to_int(y),
        lambda x, y: Predicate.to_int(x) < Predicate.to_int(y))
    GT = Relation(
        'GT',
        '$gt',
        '>',
        lambda x, y: Predicate.to_int(x) > Predicate.to_int(y),
        lambda x, y: Predicate.to_int(x) <= Predicate.to_int(y))

    @staticmethod
    def get(relation: str) -> 'Predicate':
        """Return enum instance corresponding to input relation string."""

        for pred in Predicate:
            if relation.upper() in (
                pred.value.fortran, pred.value.wql.upper(), pred.value.math
            ):
                return pred
        return None

    @staticmethod
    def to_int(value: Any) -> int:
        """
        Cast a value as its equivalent int for indy predicate argument.

        Raise ValueError for any input but int, stringified int, or boolean.

        Args:
            value: value to coerce
        """

        if isinstance(value, (bool, int)):
            return int(value)
        return int(str(value))  # kick out floats


async def indy_proof_request2indy_requested_creds(
    indy_proof_request: dict,
    holder: BaseHolder
):
    """
    Build indy requested-credentials structure.

    Given input proof request, use credentials in holder's wallet to
    build indy requested credentials structure for input to proof creation.

    Args:
        indy_proof_request: indy proof request
        holder: holder injected into current context

    """
    req_creds = {
        "self_attested_attributes": {},
        "requested_attributes": {},
        "requested_predicates": {}
    }

    for category in ("requested_attributes", "requested_predicates"):
        for referent in indy_proof_request[category]:
            credentials = (
                await holder.get_credentials_for_presentation_request_by_referent(
                    indy_proof_request,
                    (referent,),
                    0,
                    2,
                    {}
                )
            )
            if len(credentials) != 1:
                raise ValueError(
                    f"Could not automatically construct presentation for "
                    + f"presentation request {indy_proof_request['name']}"
                    + f":{indy_proof_request['version']} because referent "
                    + f"{referent} did not produce exactly one credential "
                    + f"result. The wallet returned {len(credentials)} "
                    + f"matching credentials."
                )

            req_creds[category][referent] = {
                "cred_id": credentials[0]["cred_info"]["referent"],
                "revealed": True  # TODO allow specification of unrevealed attrs?
            }

    return req_creds
