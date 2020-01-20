"""Utilities for dealing with predicates."""

from collections import namedtuple
from enum import Enum
from typing import Any


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
