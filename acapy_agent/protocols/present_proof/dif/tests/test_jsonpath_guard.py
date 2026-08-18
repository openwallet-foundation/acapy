"""Tests for the JSONPath whitelist guard."""

from unittest import TestCase

from ..jsonpath_guard import MAX_PATH_LENGTH, is_safe_jsonpath

VALID_PATHS = [
    "$.credentialSubject.store.book[*].author",
    "$.credentialSubject..author",
    "$.credentialSubject.store.*",
    "$.credentialSubject.store..price",
    "$.credentialSubject.store.book[2]",
    "$.credentialSubject.store.book[-1:]",
    "$.credentialSubject.store.book[0,1]",
    "$.credentialSubject.store.book[:2]",
    "$.credentialSubject.store.book[?(@.isbn)].author",
    "$.credentialSubject.store.book[?(@.price<10)].author",
    "$.credentialSubject.store.book[?(@.price==8.95)].author",
    "$.credentialSubject.store.book[?(@.price<30 & @.category=='fiction')].author",
    "$.credentialSubject..*",
    "$.credentialSubject.store.bicycle[?(@.color=='blue')].price",
    "$.credentialSubject.store.book[(@.length-1)]",
]

MALICIOUS_OR_UNSUPPORTED_PATHS = [
    "$.credentialSubject.store.book[?(sub(@.author,'.*','x')=='x')].title",
    "$.credentialSubject..*[?(@.ssn =~ '^[0-9]{3}-[0-9]{2}-[0-9]{4}$')]",
    "$.credentialSubject.store.book[?(@.price<30 && @.category==\"fiction\")].author",
    "$.credentialSubject.store.book[?(__import__('os').system('id'))]",
    "$.credentialSubject.store.book[?(str(@.price).length()>2)]",
    "." * (MAX_PATH_LENGTH * 2),
    "",
    None,
]


class TestJsonPathGuard(TestCase):
    """Whitelist behavior for DIF field paths."""

    def test_valid_paths_are_accepted(self):
        for path in VALID_PATHS:
            assert is_safe_jsonpath(path), f"expected valid: {path!r}"

    def test_malicious_or_unsupported_paths_are_rejected(self):
        for path in MALICIOUS_OR_UNSUPPORTED_PATHS:
            assert not is_safe_jsonpath(path), f"expected rejected: {path!r}"
