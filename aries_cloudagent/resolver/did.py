"""W3C DID.

DID Parsing rules derived from W3C Decentrialized Identifiers v1.0 Working Draft 18
January 2021:

    https://w3c.github.io/did-core/

"""

import re
from typing import Dict, Union
from urllib.parse import urlparse, parse_qsl, urlencode
from ..core.error import BaseError

DID_PATTERN = re.compile("did:([a-z0-9]+):((?:[a-zA-Z0-9._-]*:)*[a-zA-Z0-9._-]+)")


class DIDError(BaseError):
    """General did error."""


class InvalidDIDError(DIDError):
    """Invalid DID."""


class InvalidDIDUrlError(DIDError):
    """Invalid DID."""


class DIDUrl:
    """DID URL."""

    def __init__(
        self,
        did: str,
        path: str = None,
        query: Dict[str, str] = None,
        fragment: Union[str, int] = None,
    ):
        """Initialize DID URL.

        Leading '/' of path inserted if absent.
        """
        self.did = did
        if path and not path.startswith("/"):
            path = "/" + path
        self.path = path

        self.query = query
        self.fragment = str(fragment) if fragment else None
        self.url = self._stringify()

    def _stringify(self):
        """Return a DID URL.

        Leading '/' of path inserted if absent.
        Delimiters for query and fragment will be inserted.
        """
        value = self.did
        if self.path:
            value += self.path

        if self.query:
            value += "?" + urlencode(self.query)

        if self.fragment:
            value += "#" + self.fragment

        return value

    def __str__(self):
        """Return string representation of DID URL.

        Delimiters for query and fragment will be inserted.
        """
        return self.url

    def __repr__(self):
        """Return debug representation of DID URL."""
        return "<DIDUrl {}>".format(self.url)

    def __eq__(self, other):
        """Check equality."""
        if isinstance(other, str):
            return self.url == other
        if not isinstance(other, DIDUrl):
            return False
        return self.url == other.url

    def __hash__(self):
        """Hash url string."""
        return hash(self.url)

    @classmethod
    def parse(cls, url: str):
        """Parse DID URL from string."""
        matches = DID_PATTERN.match(url)

        if not matches:
            raise InvalidDIDUrlError("DID could not be parsed from URL {}.".format(url))

        did = matches.group(0)
        _, url_component = url.split(did)

        if not url_component:
            raise InvalidDIDUrlError(
                "No path, query, or fragment found in URL {}".format(url)
            )

        parts = urlparse(url_component)
        return cls(
            did,
            parts.path or None,
            dict(parse_qsl(parts.query)) if parts.query else None,
            parts.fragment or None,
        )

    @classmethod
    def as_str(
        cls,
        did: str,
        path: str = None,
        query: Dict[str, str] = None,
        fragment: str = None,
    ):
        """Form a DID URL from parts and return the string representation."""
        return str(cls(did, path, query, fragment))


class DID:
    """DID Representation and helpers."""

    def __init__(self, did: str):
        """Validate and parse raw DID str."""
        self._raw = did
        matched = DID_PATTERN.fullmatch(did)
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
        return "<DID {}>".format(self._raw)

    def __eq__(self, other):
        """Test equality."""
        if isinstance(other, str):
            return self._raw == other
        if isinstance(other, DID):
            return self._raw == other._raw

        return False

    def url(self, path: str = None, query: Dict[str, str] = None, fragment: str = None):
        """Return a DID URL for this DID."""
        return DIDUrl(self._raw, path, query, fragment)

    def ref(self, ident: str):
        """Return a DID reference (URL) for use as an ID in a DID Doc section."""
        return DIDUrl.as_str(self._raw, fragment=ident)
