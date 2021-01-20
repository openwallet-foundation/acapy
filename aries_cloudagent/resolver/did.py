"""W3C DID.

DID Parsing rules derived from W3C Decentrialized Identifiers v1.0 Working Draft 18
January 2021:

    https://w3c.github.io/did-core/

"""

import re
from typing import Dict


class InvalidDIDError(Exception):
    """Invalid DID."""


class DID:
    """DID Representation and helpers."""

    PATTERN = re.compile("did:([a-z]+):((?:[a-zA-Z0-9._-]*:)*[a-zA-Z0-9._-]+)")

    def __init__(self, did: str):
        """Validate and parse raw DID str."""
        self._raw = did
        matched = self.PATTERN.match(did)
        if not matched:
            raise InvalidDIDError("Unable to parse DID {}".format(did))
        self._method = matched.group(1)
        self._id = matched.group(2)

    @property
    def method(self):
        """Return the method of this DID."""
        return self._method

    @property
    def method_specific_id(self):
        """Return the method specific identifier."""
        return self._id

    def __str__(self):
        """Return string representation of DID."""
        return self._raw

    def __repr__(self):
        """Return debug representation of DID."""
        return self._raw

    def __eq__(self, other):
        """Test equality."""
        if isinstance(other, str):
            return self._raw == other
        if isinstance(other, DID):
            return self._raw == other._raw

        return False

    def url(self, path: str = None, query: Dict[str, str] = None, fragment: str = None):
        """Return a DID URL.

        Leading '/' of path inserted if absent.
        Delimiters for query and fragment will be inserted.
        """
        stem = str(self)
        path = path or ""
        if path and not path.startswith("/"):
            path = "/" + path

        query = query or ""
        if query:
            query = "?" + "&".join(
                ["{}={}".format(key, value) for key, value in query.items()]
            )

        fragment = fragment or ""
        if fragment:
            fragment = "#" + fragment

        return "{}{}{}{}".format(stem, path, query, fragment)
