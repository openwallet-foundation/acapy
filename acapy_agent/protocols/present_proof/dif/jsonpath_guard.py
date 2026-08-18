"""Whitelist validator for JSONPath expressions in DIF field paths.

Presentation requests are only secured at the DIDComm connection level —
nothing validates the *content* of an incoming request. Since ACA-Py parses
each field's JSONPath with ``jsonpath_ng.ext``, an untrusted sender could
include a malformed or function-extension-based expression (``sub()``,
``str()``, ``sorted()``, ``search()``, ``match()``, regex via ``=~``) that
either crashes the whole presentation or evaluates logic we never intended
to support.

Rather than trying to detect "is this expression malicious," this module
does the safer inverse: only expressions matching a fixed, narrow, known-safe
grammar are accepted. Anything else — malicious or merely unsupported — is
rejected the same way, before it ever reaches the real parser.
"""

import re

_NAME = r"[A-Za-z_][A-Za-z0-9_-]*"
_LITERAL = r"(?:-?\d+(?:\.\d+)?|'[^']*'|\"[^\"]*\"|true|false)"
_OP = r"(?:<=|>=|==|!=|<|>)"
_EXISTS = rf"@\.{_NAME}"
_COND = rf"@\.{_NAME}\s*{_OP}\s*{_LITERAL}"
_ONE_COND = rf"(?:{_COND}|{_EXISTS})"
_FILTER = rf"\?\({_ONE_COND}(?:\s*&\s*{_ONE_COND})?\)"
_SCRIPT_LEN = r"\(@\.length\s*-\s*\d+\)"
_INDEX = r"-?\d+"
_SLICE = r"-?\d*:-?\d*(?::-?\d*)?"
_UNION = r"-?\d+(?:,\s*-?\d+)+"
_BRACKET = rf"\[(?:\*|{_INDEX}|{_SLICE}|{_UNION}|{_FILTER}|{_SCRIPT_LEN})\]"
_SEGMENT = rf"(?:\.\.(?:{_NAME}|\*)|\.(?:{_NAME}|\*)|{_BRACKET})"

SAFE_JSONPATH_RE = re.compile(rf"^\$?{_SEGMENT}*$")

MAX_PATH_LENGTH = 200
MAX_SEGMENTS = 12


def is_safe_jsonpath(path: str) -> bool:
    """Return True if ``path`` matches the supported, known-safe JSONPath grammar.

    Supports: child access, wildcard (``*``/``.*``), recursive descent
    (``..name``/``..*``), index (``[n]``), slice (``[n:m]``), union
    (``[n,m]``), the ``@.length-N`` script subscript, and filter expressions
    (``[?(...)]``) limited to bare-existence or single-comparison conditions,
    optionally joined by one ``&``.

    Deliberately excludes: function-extension calls (``sub``, ``str``,
    ``sorted``, ``search``, ``match``, ``filter``), the ``=~`` regex operator,
    ``&&``, and anything else outside this grammar — including expressions
    that are merely unsupported rather than actively malicious.
    """
    if not path or len(path) > MAX_PATH_LENGTH:
        return False
    if path.count(".") + path.count("[") > MAX_SEGMENTS * 2:
        return False
    return bool(SAFE_JSONPATH_RE.match(path))
