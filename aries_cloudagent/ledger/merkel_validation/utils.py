from binascii import hexlify, unhexlify
import base58
import hashlib
import msgpack

from typing import List, Dict
from rlp.sedes import big_endian_int
from rlp import encode, decode
from collections import OrderedDict

hash_function = hashlib.sha256()


def sha3_256(x):
    return hashlib.sha3_256(x).digest()


def is_numeric(x):
    return isinstance(x, int)


def is_string(x):
    return isinstance(x, bytes)


def encode_hex(b):
    if isinstance(b, str):
        b = bytes(b, "utf-8")
    if isinstance(b, bytes):
        return str(hexlify(b), "utf-8")
    raise TypeError("Value must be an instance of str or bytes")


def to_string(value):
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return bytes(value, "utf-8")
    if isinstance(value, int):
        return bytes(str(value), "utf-8")


def sha3(seed):
    return sha3_256(to_string(seed))


def int_to_big_endian(x):
    return big_endian_int.serialize(x)


NIBBLE_TERMINATOR = 16
hti = {c: i for i, c in enumerate("0123456789abcdef")}


def bin_to_nibbles(s):
    return [hti[c] for c in encode_hex(s)]


def nibbles_to_bin(nibbles):
    if any(x > 15 or x < 0 for x in nibbles):
        raise Exception("nibbles can only be [0,..15]")

    if len(nibbles) % 2:
        raise Exception("nibbles must be of even numbers")

    res = b""
    for i in range(0, len(nibbles), 2):
        res += ascii_chr(16 * nibbles[i] + nibbles[i + 1])
    return res


def key_nibbles_from_key_value_node(node):
    return without_terminator(unpack_to_nibbles(node[0]))


def with_terminator(nibbles):
    nibbles = nibbles[:]
    if not nibbles or nibbles[-1] != NIBBLE_TERMINATOR:
        nibbles.append(NIBBLE_TERMINATOR)
    return nibbles


def without_terminator(nibbles):
    nibbles = nibbles[:]
    if nibbles and nibbles[-1] == NIBBLE_TERMINATOR:
        del nibbles[-1]
    return nibbles


def adapt_terminator(nibbles, has_terminator):
    if has_terminator:
        return with_terminator(nibbles)
    else:
        return without_terminator(nibbles)


def without_terminator_and_flags(nibbles):
    nibbles = nibbles[:]
    if nibbles and nibbles[-1] == NIBBLE_TERMINATOR:
        del nibbles[-1]
    if len(nibbles) % 2:
        del nibbles[0]
    return nibbles


def pack_nibbles(nibbles):
    """pack nibbles to binary

    :param nibbles: a nibbles sequence. may have a terminator
    """

    if nibbles[-1] == NIBBLE_TERMINATOR:
        flags = 2
        nibbles = nibbles[:-1]
    else:
        flags = 0

    oddlen = len(nibbles) % 2
    flags |= oddlen  # set lowest bit if odd number of nibbles
    if oddlen:
        nibbles = [flags] + nibbles
    else:
        nibbles = [flags, 0] + nibbles
    o = b""
    for i in range(0, len(nibbles), 2):
        o += ascii_chr(16 * nibbles[i] + nibbles[i + 1])
    return o


def unpack_to_nibbles(bindata):
    """unpack packed binary data to nibbles

    :param bindata: binary packed from nibbles
    :return: nibbles sequence, may have a terminator
    """
    o = bin_to_nibbles(bindata)
    flags = o[0]
    if flags & 2:
        o.append(NIBBLE_TERMINATOR)
    if flags & 1 == 1:
        o = o[1:]
    else:
        o = o[2:]
    return o


def starts_with(full, part):
    """test whether the items in the part is
    the leading items of the full
    """
    if len(full) < len(part):
        return False
    return full[: len(part)] == part


def audit_path_length(index: int, tree_size: int):
    length = 0
    last_node = tree_size - 1
    while last_node > 0:
        if index % 2 or index < last_node:
            length += 1
        index //= 2
        last_node //= 2

    return length


def ascii_chr(value):
    return bytes([value])


def to_string(value):
    if isinstance(value, (bytes, bytearray)):
        return value
    elif isinstance(value, str):
        value = value.encode()
        return value
    else:
        value = str(value)
        value = value.encode()
        return bytes(value)


def to_hex(value):
    return to_string(value).hex()


def decode_to_sorted(obj):
    return OrderedDict(obj)


def sort_dict(d) -> OrderedDict:
    if not isinstance(d, Dict):
        return d
    d = OrderedDict(sorted(d.items()))
    for k, v in d.items():
        if isinstance(v, Dict):
            d[k] = sort_dict(v)
        if isinstance(v, List):
            d[k] = [sort_dict(sub_v) for sub_v in v]
    return d
