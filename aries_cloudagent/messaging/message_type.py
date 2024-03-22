"""Utilities for working with Message Types and Versions."""

from dataclasses import dataclass
from functools import lru_cache
import re
from typing import ClassVar, Pattern, Tuple, Union


@dataclass
class MessageVersion:
    """Message type version."""

    PATTERN: ClassVar[Pattern] = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$")

    major: int
    minor: int

    @classmethod
    @lru_cache
    def from_str(cls, value: str):
        """Parse a version string."""
        if match := cls.PATTERN.match(value):
            return cls(
                int(match.group(1)),
                int(match.group(2)),
            )

        raise ValueError(f"Invalid version: {value}")

    def __gt__(self, other: "MessageVersion") -> bool:
        """Test whether this version is greater than another."""
        if self.major != other.major:
            return self.major > other.major
        return self.minor > other.minor

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, MessageVersion):
            return False

        return self.major == other.major and self.minor == other.minor

    def __lt__(self, other: "MessageVersion") -> bool:
        """Test whether this version is less than another."""
        if self.major != other.major:
            return self.major < other.major
        return self.minor < other.minor

    def __str__(self) -> str:
        """Return the version as a string."""
        return f"{self.major}.{self.minor}"

    def __hash__(self) -> int:
        """Return a hash of the version."""
        return hash((self.major, self.minor))

    def compatible(self, other: "MessageVersion") -> bool:
        """Test whether this version is compatible with another."""
        if self == other:
            return True
        return self.major == other.major and self.minor <= other.minor


@dataclass
class ProtocolIdentifier:
    """Protocol identifier."""

    PATTERN: ClassVar[Pattern] = re.compile(r"^(.*?)/([a-z0-9._-]+)/(\d[^/]*)$")
    FROM_MESSAGE_TYPE_PATTERN: ClassVar[Pattern] = re.compile(
        r"^(.*?)/([a-z0-9._-]+)/(\d[^/]*).*$"
    )

    doc_uri: str
    protocol: str
    version: MessageVersion

    @classmethod
    @lru_cache
    def from_str(cls, value: str) -> "ProtocolIdentifier":
        """Parse a protocol identifier string."""
        if match := cls.PATTERN.match(value):
            return cls(
                doc_uri=match.group(1),
                protocol=match.group(2),
                version=MessageVersion.from_str(match.group(3)),
            )
        raise ValueError(f"Invalid protocol identifier: {value}")

    @classmethod
    @lru_cache
    def from_message_type(
        cls, message_type: Union[str, "MessageType"]
    ) -> "ProtocolIdentifier":
        """Create a protocol identifier from a message type."""
        if isinstance(message_type, str):
            if match := cls.FROM_MESSAGE_TYPE_PATTERN.match(message_type):
                return cls(
                    doc_uri=match.group(1),
                    protocol=match.group(2),
                    version=MessageVersion.from_str(match.group(3)),
                )

            raise ValueError(f"Invalid protocol identifier: {message_type}")
        elif isinstance(message_type, MessageType):
            return cls(
                message_type.doc_uri, message_type.protocol, message_type.version
            )
        else:
            raise TypeError(f"Invalid message type: {message_type}")

    def __str__(self) -> str:
        """Return the protocol identifier as a string."""
        return f"{self.doc_uri}/{self.protocol}/{self.version}"

    @property
    def stem(self) -> str:
        """Return the protocol stem, including doc_uri, protocol, and major version."""
        return f"{self.doc_uri}/{self.protocol}/{self.version.major}"

    def with_version(
        self, version: Union[str, MessageVersion, Tuple[int, int]]
    ) -> "ProtocolIdentifier":
        """Return a new protocol identifier with the specified version."""
        if isinstance(version, str):
            version = MessageVersion.from_str(version)

        if isinstance(version, tuple):
            version = MessageVersion(*version)

        return ProtocolIdentifier(
            doc_uri=self.doc_uri,
            protocol=self.protocol,
            version=version,
        )


@dataclass
class MessageType:
    """Message type."""

    PATTERN: ClassVar[Pattern] = re.compile(
        r"^(.*?)/([a-z0-9._-]+)/(\d[^/]*)/([a-z0-9._-]+)$"
    )

    doc_uri: str
    protocol: str
    version: MessageVersion
    name: str

    @classmethod
    @lru_cache
    def from_str(cls, value: str):
        """Parse a message type string."""
        if match := cls.PATTERN.match(value):
            return cls(
                doc_uri=match.group(1),
                protocol=match.group(2),
                version=MessageVersion.from_str(match.group(3)),
                name=match.group(4),
            )

        raise ValueError(f"Invalid message type: {value}")

    def __str__(self) -> str:
        """Return the message type as a string."""
        return f"{self.doc_uri}/{self.protocol}/{self.version}/{self.name}"

    def with_version(
        self, version: Union[str, MessageVersion, Tuple[int, int]]
    ) -> "MessageType":
        """Return a new message type with the specified version."""
        if isinstance(version, str):
            version = MessageVersion.from_str(version)

        if isinstance(version, tuple):
            version = MessageVersion(*version)

        return MessageType(
            doc_uri=self.doc_uri,
            protocol=self.protocol,
            version=version,
            name=self.name,
        )

    def __hash__(self) -> int:
        """Return a hash of the message type."""
        return hash((self.doc_uri, self.protocol, self.version, self.name))


class MessageTypeStr(str):
    """Message type string."""

    def __init__(self, value: str):
        """Initialize the message type string."""
        super().__init__()
        self._parsed = MessageType.from_str(value)

    @property
    def parsed(self) -> MessageType:
        """Return the parsed message type."""
        return self._parsed

    @property
    def doc_uri(self) -> str:
        """Return the message type document URI."""
        return self._parsed.doc_uri

    @property
    def protocol(self) -> str:
        """Return the message type protocol."""
        return self._parsed.protocol

    @property
    def version(self) -> MessageVersion:
        """Return the message type version."""
        return self._parsed.version

    @property
    def name(self) -> str:
        """Return the message type name."""
        return self._parsed.name

    @property
    def protocol_identifier(self) -> ProtocolIdentifier:
        """Return the message type protocol identifier."""
        return ProtocolIdentifier.from_message_type(self._parsed)

    def with_version(
        self, version: Union[str, MessageVersion, Tuple[int, int]]
    ) -> "MessageTypeStr":
        """Return a new message type string with the specified version."""
        return MessageTypeStr(str(self._parsed.with_version(version)))
