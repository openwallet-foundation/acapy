"""Database types and data structures for database manager."""

import json
from enum import Enum
from typing import Optional, Sequence


class KeyAlg(Enum):
    """Enumeration of supported key algorithms."""

    A128GCM = "a128gcm"
    A256GCM = "a256gcm"
    A128CBC_HS256 = "a128cbchs256"
    A256CBC_HS512 = "a256cbchs512"
    A128KW = "a128kw"
    A256KW = "a256kw"
    BLS12_381_G1 = "bls12381g1"
    BLS12_381_G2 = "bls12381g2"
    BLS12_381_G1G2 = "bls12381g1g2"
    C20P = "c20p"
    XC20P = "xc20p"
    ED25519 = "ed25519"
    X25519 = "x25519"
    K256 = "k256"
    P256 = "p256"

    @classmethod
    def from_key_alg(cls, alg: str) -> Optional["KeyAlg"]:
        """Get KeyAlg instance from the algorithm identifier."""
        for cmp_alg in KeyAlg:
            if cmp_alg.value == alg:
                return cmp_alg
        return None


class SeedMethod(Enum):
    """Enumeration of supported seed methods."""

    BlsKeyGen = "bls_keygen"

    @classmethod
    def from_seed_method(cls, method: str) -> Optional["SeedMethod"]:
        """Get SeedMethod instance from the method identifier."""
        for cmp_mth in SeedMethod:
            if cmp_mth.value == method:
                return cmp_mth
        return None


class EntryOperation(Enum):
    """Enumeration of database entry operations."""

    INSERT = 0
    REPLACE = 1
    REMOVE = 2


class Entry:
    """A single result from a store query."""

    _KEYS = ("name", "category", "value", "tags")

    def __init__(self, category: str, name: str, value: str | bytes, tags: dict):
        """Initialize Entry."""
        self._category = category
        self._name = name
        # Store value as string; decode bytes to UTF-8 if necessary
        self._value = value.decode("utf-8") if isinstance(value, bytes) else value
        self._tags = tags

    @property
    def category(self) -> str:
        """Get the entry category."""
        return self._category

    @property
    def name(self) -> str:
        """Get the entry name."""
        return self._name

    @property
    def value(self) -> str:
        """Get the entry value."""
        return self._value

    @property
    def raw_value(self) -> memoryview:
        """Get the entry value as raw bytes."""
        return memoryview(self._value.encode())

    @property
    def value_json(self) -> dict:
        """Get the entry value parsed as JSON."""
        return json.loads(self._value)

    @property
    def tags(self) -> dict:
        """Get the entry tags."""
        return self._tags

    def keys(self):
        """Get the entry keys."""
        return self._KEYS

    def __getitem__(self, key):
        """Get item by key."""
        if key in self._KEYS:
            return getattr(self, key)
        raise KeyError

    def __repr__(self) -> str:
        """Return string representation of Entry."""
        return (
            f"<Entry(category={repr(self.category)}, name={repr(self.name)}, "
            f"value={self.value}, tags={self.tags})>"
        )


class EntryList:
    """A list of Entry objects."""

    def __init__(self, entries: Sequence[Entry], length: int = None):
        """Initialize EntryList."""
        self._entries = entries
        self._length = length if length is not None else len(entries)

    @property
    def handle(self):
        """Get dummy handle for compatibility."""
        return id(self)  # Dummy handle for compatibility

    def __getitem__(self, index) -> Entry:
        """Get entry by index."""
        if not isinstance(index, int) or index < 0 or index >= self._length:
            raise IndexError()
        return self._entries[index]

    def __iter__(self):
        """Return iterator over entries."""
        return IterEntryList(self)

    def __len__(self) -> int:
        """Get length of entry list."""
        return self._length

    def __repr__(self) -> str:
        """Return string representation of EntryList."""
        return f"<EntryList(handle={self.handle}, length={self._length})>"


class IterEntryList:
    """Iterator for EntryList."""

    def __init__(self, list: EntryList):
        """Initialize IterEntryList."""
        self._entries = list._entries
        self._len = list._length
        self._pos = 0

    def __next__(self):
        """Get next entry."""
        if self._pos < self._len:
            entry = self._entries[self._pos]
            self._pos += 1
            return entry
        raise StopIteration
