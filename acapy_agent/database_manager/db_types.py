from enum import Enum
from typing import Optional, Union, Sequence
import json

class KeyAlg(Enum):
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
    BlsKeyGen = "bls_keygen"

    @classmethod
    def from_seed_method(cls, method: str) -> Optional["SeedMethod"]:
        """Get SeedMethod instance from the method identifier."""
        for cmp_mth in SeedMethod:
            if cmp_mth.value == method:
                return cmp_mth
        return None

class EntryOperation(Enum):
    INSERT = 0
    REPLACE = 1
    REMOVE = 2

class Entry:
    """A single result from a store query."""
    _KEYS = ("name", "category", "value", "tags")

    def __init__(self, category: str, name: str, value: Union[str, bytes], tags: dict):
        self._category = category
        self._name = name
        # Store value as string; decode bytes to UTF-8 if necessary
        self._value = value.decode('utf-8') if isinstance(value, bytes) else value
        self._tags = tags

    @property
    def category(self) -> str:
        return self._category

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> str:
        return self._value

    @property
    def raw_value(self) -> memoryview:
        return memoryview(self._value.encode())

    @property
    def value_json(self) -> dict:
        return json.loads(self._value)

    @property
    def tags(self) -> dict:
        return self._tags

    def keys(self):
        return self._KEYS

    def __getitem__(self, key):
        if key in self._KEYS:
            return getattr(self, key)
        raise KeyError

    def __repr__(self) -> str:
        return f"<Entry(category={repr(self.category)}, name={repr(self.name)}, value={self.value}, tags={self.tags})>"

class EntryList:
    """A list of Entry objects."""
    def __init__(self, entries: Sequence[Entry], length: int = None):
        self._entries = entries
        self._length = length if length is not None else len(entries)

    @property
    def handle(self):
        return id(self)  # Dummy handle for compatibility

    def __getitem__(self, index) -> Entry:
        if not isinstance(index, int) or index < 0 or index >= self._length:
            raise IndexError()
        return self._entries[index]

    def __iter__(self):
        return IterEntryList(self)

    def __len__(self) -> int:
        return self._length

    def __repr__(self) -> str:
        return f"<EntryList(handle={self.handle}, length={self._length})>"

class IterEntryList:
    """Iterator for EntryList."""
    def __init__(self, list: EntryList):
        self._entries = list._entries
        self._len = list._length
        self._pos = 0

    def __next__(self):
        if self._pos < self._len:
            entry = self._entries[self._pos]
            self._pos += 1
            return entry
        raise StopIteration