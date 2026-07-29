from unittest import TestCase

from ..auth_context import (
    AUTH_SCOPES_SETTING,
    AUTH_SUBJECT_SETTING,
    AUTH_WALLET_ID_SETTING,
    get_auth_scopes,
    get_auth_subject,
    get_auth_wallet_id,
    has_auth_scopes,
    has_auth_wallet_id,
)


class _DummyContext:
    def __init__(self, metadata=None, settings=None):
        self.metadata = metadata
        self.settings = settings if settings is not None else {}


class TestAuthContextHelpers(TestCase):
    def test_scopes_from_metadata(self):
        context = _DummyContext(metadata={"scopes": {"acapy:admin"}})

        assert has_auth_scopes(context)
        assert get_auth_scopes(context) == {"acapy:admin"}

    def test_scopes_from_settings_fallback(self):
        context = _DummyContext(settings={AUTH_SCOPES_SETTING: ("acapy:tenant",)})

        assert has_auth_scopes(context)
        assert get_auth_scopes(context) == {"acapy:tenant"}

    def test_subject_from_settings_fallback(self):
        context = _DummyContext(settings={AUTH_SUBJECT_SETTING: "alice"})

        assert get_auth_subject(context) == "alice"

    def test_wallet_id_prefers_metadata_then_settings(self):
        context = _DummyContext(
            metadata={"wallet_id": "metadata-wallet"},
            settings={AUTH_WALLET_ID_SETTING: "settings-wallet"},
        )

        assert has_auth_wallet_id(context)
        assert get_auth_wallet_id(context) == "metadata-wallet"

    def test_wallet_id_from_settings_when_metadata_missing(self):
        context = _DummyContext(settings={AUTH_WALLET_ID_SETTING: "settings-wallet"})

        assert has_auth_wallet_id(context)
        assert get_auth_wallet_id(context) == "settings-wallet"

    def test_non_mapping_settings_treated_as_empty(self):
        context = _DummyContext(settings="not-a-mapping")

        assert not has_auth_scopes(context)
        assert get_auth_scopes(context) == set()
        assert get_auth_subject(context) is None
        assert get_auth_wallet_id(context) is None

    def test_scopes_from_string_and_invalid_types(self):
        context = _DummyContext(metadata={"scopes": "acapy:tenant acapy:admin"})
        assert get_auth_scopes(context) == {"acapy:tenant", "acapy:admin"}

        context = _DummyContext(metadata={"scopes": {"acapy:tenant", 42}})
        assert get_auth_scopes(context) == {"acapy:tenant"}

        context = _DummyContext(metadata={"scopes": 42})
        assert get_auth_scopes(context) == set()
