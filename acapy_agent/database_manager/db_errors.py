"""Unified database error helpers across Askar and DBStore.

Provides a common tuple of exception types and grouped error-code sets so
business logic can remain agnostic to the underlying storage backend.
"""

from typing import FrozenSet, Tuple, Type, Union

from aries_askar import AskarError, AskarErrorCode

from .error import DBStoreError, DBStoreErrorCode

DBError: Tuple[Type[AskarError], Type[DBStoreError]] = (AskarError, DBStoreError)

DBCodeUnion = Union[AskarErrorCode, DBStoreErrorCode]


class DBCode:
    """Unified code groups: use in membership checks.

    Example:
        try:
            repo.save(record)
        except DBError as err:
            if err.code not in DBCode.DUPLICATE:
                raise

    """

    DUPLICATE: FrozenSet[DBCodeUnion] = frozenset(
        {AskarErrorCode.DUPLICATE, DBStoreErrorCode.DUPLICATE}
    )
    NOT_FOUND: FrozenSet[DBCodeUnion] = frozenset(
        {AskarErrorCode.NOT_FOUND, DBStoreErrorCode.NOT_FOUND}
    )
