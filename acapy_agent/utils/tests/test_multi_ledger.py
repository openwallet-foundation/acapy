from unittest import TestCase

from ...config.settings import Settings
from ...core.error import ProfileError
from ..multi_ledger import get_write_ledger_config_for_profile

PROD_WRITE = {"id": "prod-write", "is_production": True, "is_write": True}
PROD_READ_ONLY = {"id": "prod-read-only", "is_production": True, "read_only": True}
NON_PROD_WRITE = {"id": "non-prod-write", "is_production": False, "is_write": True}
NON_PROD_NEITHER = {"id": "non-prod-neither", "is_production": False}


def make_settings(ledger_config_list, write_ledger=None) -> Settings:
    settings = Settings({"ledger.ledger_config_list": ledger_config_list})
    if write_ledger:
        settings["ledger.write_ledger"] = write_ledger
    return settings


class TestGetWriteLedgerConfigForProfile(TestCase):
    def test_write_ledger_in_prod_pool(self):
        settings = make_settings([PROD_WRITE, NON_PROD_WRITE], write_ledger="prod-write")
        assert get_write_ledger_config_for_profile(settings) == PROD_WRITE

    def test_write_ledger_in_non_prod_pool(self):
        settings = make_settings(
            [PROD_WRITE, NON_PROD_WRITE], write_ledger="non-prod-write"
        )
        assert get_write_ledger_config_for_profile(settings) == NON_PROD_WRITE

    def test_read_only_ledger_is_write_configurable(self):
        settings = make_settings(
            [PROD_WRITE, PROD_READ_ONLY], write_ledger="prod-read-only"
        )
        assert get_write_ledger_config_for_profile(settings) == PROD_READ_ONLY

    def test_unconfigured_write_ledger_falls_back_to_prod_default(self):
        # e.g. the ledger selected via set-write-ledger was later removed
        # from --genesis-transactions-list
        settings = make_settings(
            [PROD_WRITE, NON_PROD_WRITE], write_ledger="decommissioned"
        )
        assert get_write_ledger_config_for_profile(settings) == PROD_WRITE

    def test_unconfigured_write_ledger_falls_back_to_non_prod_default(self):
        settings = make_settings([NON_PROD_WRITE], write_ledger="decommissioned")
        assert get_write_ledger_config_for_profile(settings) == NON_PROD_WRITE

    def test_no_write_ledger_uses_prod_default(self):
        settings = make_settings([NON_PROD_WRITE, PROD_WRITE])
        assert get_write_ledger_config_for_profile(settings) == PROD_WRITE

    def test_no_write_ledger_uses_non_prod_default(self):
        settings = make_settings([NON_PROD_NEITHER, NON_PROD_WRITE])
        assert get_write_ledger_config_for_profile(settings) == NON_PROD_WRITE

    def test_no_write_configurable_ledgers_raises(self):
        settings = make_settings([NON_PROD_NEITHER])
        with self.assertRaises(ProfileError):
            get_write_ledger_config_for_profile(settings)

    def test_unconfigured_write_ledger_no_default_raises(self):
        settings = make_settings([NON_PROD_NEITHER], write_ledger="decommissioned")
        with self.assertRaises(ProfileError):
            get_write_ledger_config_for_profile(settings)
