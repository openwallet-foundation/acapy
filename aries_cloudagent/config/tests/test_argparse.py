from configargparse import ArgumentTypeError

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from .. import argparse
from ..util import BoundedInt, ByteSize


class TestArgParse(AsyncTestCase):
    async def test_groups(self):
        """Test optional argument parsing."""
        parser = argparse.create_argument_parser()

        groups = (
            g
            for g in argparse.group.get_registered()
            if g is not argparse.TransportGroup
        )
        argparse.load_argument_groups(parser, *groups)

        parser.parse_args([])

    async def test_transport_settings(self):
        """Test required argument parsing."""

        parser = argparse.create_argument_parser()
        group = argparse.TransportGroup()
        group.add_arguments(parser)

        with async_mock.patch.object(parser, "exit") as exit_parser:
            parser.parse_args(["-h"])
            exit_parser.assert_called_once()

        result = parser.parse_args(
            [
                "--inbound-transport",
                "http",
                "0.0.0.0",
                "80",
                "--outbound-transport",
                "http",
                "--max-outbound-retry",
                "5",
            ]
        )

        assert result.inbound_transports == [["http", "0.0.0.0", "80"]]
        assert result.outbound_transports == ["http"]

        settings = group.get_settings(result)

        assert settings.get("transport.inbound_configs") == [["http", "0.0.0.0", "80"]]
        assert settings.get("transport.outbound_configs") == ["http"]
        assert result.max_outbound_retry == 5

    async def test_get_genesis_transactions_list_with_ledger_selection(self):
        """Test multiple ledger support related argument parsing."""

        parser = argparse.create_argument_parser()
        group = argparse.LedgerGroup()
        group.add_arguments(parser)

        with async_mock.patch.object(parser, "exit") as exit_parser:
            parser.parse_args(["-h"])
            exit_parser.assert_called_once()

        result = parser.parse_args(
            [
                "--genesis-transactions-list",
                "./aries_cloudagent/config/tests/test-ledger-args.yaml",
            ]
        )

        assert (
            result.genesis_transactions_list
            == "./aries_cloudagent/config/tests/test-ledger-args.yaml"
        )

        settings = group.get_settings(result)

        assert len(settings.get("ledger.ledger_config_list")) == 3
        assert (
            {
                "id": "sovrinStaging",
                "is_production": True,
                "genesis_file": "/home/indy/ledger/sandbox/pool_transactions_genesis",
            }
        ) in settings.get("ledger.ledger_config_list")
        assert (
            {
                "id": "sovrinTest",
                "is_production": False,
                "genesis_url": "http://localhost:9000/genesis",
            }
        ) in settings.get("ledger.ledger_config_list")

    async def test_upgrade_config(self):
        """Test upgrade command related argument parsing."""

        parser = argparse.create_argument_parser()
        group = argparse.UpgradeGroup()
        group.add_arguments(parser)

        with async_mock.patch.object(parser, "exit") as exit_parser:
            parser.parse_args(["-h"])
            exit_parser.assert_called_once()

        result = parser.parse_args(
            [
                "--upgrade-config-path",
                "./aries_cloudagent/config/tests/test-acapy-upgrade-config.yml",
                "--from-version",
                "v0.7.2",
                "--force-upgrade",
            ]
        )

        assert (
            result.upgrade_config_path
            == "./aries_cloudagent/config/tests/test-acapy-upgrade-config.yml"
        )
        assert result.force_upgrade is True

        settings = group.get_settings(result)

        assert (
            settings.get("upgrade.config_path")
            == "./aries_cloudagent/config/tests/test-acapy-upgrade-config.yml"
        )

    async def test_outbound_is_required(self):
        """Test that either -ot or -oq are required"""
        parser = argparse.create_argument_parser()
        group = argparse.TransportGroup()
        group.add_arguments(parser)

        result = parser.parse_args(
            [
                "--inbound-transport",
                "http",
                "0.0.0.0",
                "80",
            ]
        )

        with self.assertRaises(argparse.ArgsParseError):
            settings = group.get_settings(result)

    async def test_general_settings_file(self):
        """Test file argument parsing."""

        parser = argparse.create_argument_parser()
        group = argparse.GeneralGroup()
        group.add_arguments(parser)

        with async_mock.patch.object(parser, "exit") as exit_parser:
            parser.parse_args(["-h"])
            exit_parser.assert_called_once()

        result = parser.parse_args(
            [
                "--arg-file",
                "./aries_cloudagent/config/tests/test-general-args.yaml",
            ]
        )

        assert result.external_plugins == ["foo"]
        assert result.storage_type == "bar"

        settings = group.get_settings(result)

        assert settings.get("external_plugins") == ["foo"]
        assert settings.get("storage_type") == "bar"

    async def test_plugin_config_file(self):
        """Test file argument parsing."""

        parser = argparse.create_argument_parser()
        group = argparse.GeneralGroup()
        group.add_arguments(parser)

        result = parser.parse_args(
            [
                "--endpoint",
                "localhost",
                "--plugin-config",
                "./aries_cloudagent/config/tests/test_plugins_config.yaml",
            ]
        )

        assert (
            result.plugin_config
            == "./aries_cloudagent/config/tests/test_plugins_config.yaml"
        )

        settings = group.get_settings(result)

        assert settings.get("plugin_config").get("mock_resolver") == {
            "methods": ["sov", "btcr"]
        }

    async def test_transport_settings_file(self):
        """Test file argument parsing."""

        parser = argparse.create_argument_parser()
        group = argparse.GeneralGroup()
        group.add_arguments(parser)
        group = argparse.TransportGroup()
        group.add_arguments(parser)

        with async_mock.patch.object(parser, "exit") as exit_parser:
            parser.parse_args(["-h"])
            exit_parser.assert_called_once()

        result = parser.parse_args(
            [
                "--arg-file",
                "./aries_cloudagent/config/tests/test-transport-args.yaml",
            ]
        )
        # no asserts, just testing that the parser doesn't fail

    async def test_multitenancy_settings(self):
        """Test required argument parsing."""

        parser = argparse.create_argument_parser()
        group = argparse.MultitenantGroup()
        group.add_arguments(parser)

        result = parser.parse_args(
            [
                "--multitenant",
                "--jwt-secret",
                "secret",
                "--multitenancy-config",
                '{"wallet_type":"askar","wallet_name":"test", "cache_size": 10}',
                "--base-wallet-routes",
                "/my_route",
            ]
        )

        settings = group.get_settings(result)

        assert settings.get("multitenant.enabled") == True
        assert settings.get("multitenant.jwt_secret") == "secret"
        assert settings.get("multitenant.wallet_type") == "askar"
        assert settings.get("multitenant.wallet_name") == "test"
        assert settings.get("multitenant.base_wallet_routes") == ["/my_route"]

        result = parser.parse_args(
            [
                "--multitenant",
                "--jwt-secret",
                "secret",
                "--multitenancy-config",
                "wallet_type=askar",
                "wallet_name=test",
                "cache_size=10",
                "--base-wallet-routes",
                "/my_route",
            ]
        )

        settings = group.get_settings(result)

        assert settings.get("multitenant.enabled") == True
        assert settings.get("multitenant.jwt_secret") == "secret"
        assert settings.get("multitenant.wallet_type") == "askar"
        assert settings.get("multitenant.wallet_name") == "test"
        assert settings.get("multitenant.base_wallet_routes") == ["/my_route"]

    async def test_endorser_settings(self):
        """Test required argument parsing."""

        parser = argparse.create_argument_parser()
        group = argparse.EndorsementGroup()
        group.add_arguments(parser)

        result = parser.parse_args(
            [
                "--endorser-protocol-role",
                argparse.ENDORSER_AUTHOR,
                "--endorser-public-did",
                "did:sov:12345",
            ]
        )

        settings = group.get_settings(result)

        assert settings.get("endorser.author") == True
        assert settings.get("endorser.endorser") == False
        assert settings.get("endorser.endorser_public_did") == "did:sov:12345"
        assert settings.get("endorser.auto_endorse") == False

    async def test_error_raised_when_multitenancy_used_and_no_jwt_provided(self):
        """Test that error is raised if no jwt_secret is provided with multitenancy."""

        parser = argparse.create_argument_parser()
        group = argparse.MultitenantGroup()
        group.add_arguments(parser)

        result = parser.parse_args(
            [
                "--multitenant",
                "--multitenancy-config",
                '{"wallet_type":"askar","wallet_name":"test"}',
            ]
        )

        with self.assertRaises(argparse.ArgsParseError):
            settings = group.get_settings(result)

    def test_bytesize(self):
        bs = ByteSize()
        with self.assertRaises(ArgumentTypeError):
            bs(None)
        with self.assertRaises(ArgumentTypeError):
            bs("")
        with self.assertRaises(ArgumentTypeError):
            bs("a")
        with self.assertRaises(ArgumentTypeError):
            bs("1.5")
        with self.assertRaises(ArgumentTypeError):
            bs("-1")
        assert bs("101") == 101
        assert bs("101b") == 101
        assert bs("101KB") == 103424
        assert bs("2M") == 2097152
        assert bs("1G") == 1073741824
        assert bs("1t") == 1099511627776

        bs = ByteSize(min=10)
        with self.assertRaises(ArgumentTypeError):
            bs("5")
        assert bs("12") == 12

        bs = ByteSize(max=10)
        with self.assertRaises(ArgumentTypeError):
            bs("15")
        assert bs("10") == 10

        assert repr(bs) == "bytes"

    def test_bounded_int(self):
        bounded = BoundedInt()
        with self.assertRaises(ArgumentTypeError):
            bounded(None)
        with self.assertRaises(ArgumentTypeError):
            bounded("")
        with self.assertRaises(ArgumentTypeError):
            bounded("a")
        with self.assertRaises(ArgumentTypeError):
            bounded("1.5")
        assert bounded("101") == 101
        assert bounded("-99") == -99

        bounded = BoundedInt(min=10)
        with self.assertRaises(ArgumentTypeError):
            bounded("5")
        assert bounded("12") == 12

        bounded = BoundedInt(max=10)
        with self.assertRaises(ArgumentTypeError):
            bounded("15")
        assert bounded("10") == 10

        assert repr(bounded) == "integer"

    async def test_mediation_x_clear_and_default(self):
        parser = argparse.create_argument_parser()
        group = argparse.MediationGroup()
        group.add_arguments(parser)

        with self.assertRaises(argparse.ArgsParseError):
            args = parser.parse_args(
                ["--clear-default-mediator", "--default-mediator-id", "asdf"]
            )
            group.get_settings(args)

    def test_plugin_config_value_parsing(self):
        required_args = ["-e", "http://localhost:3000"]
        parser = argparse.create_argument_parser()
        group = argparse.GeneralGroup()
        group.add_arguments(parser)
        args = parser.parse_args(
            [
                *required_args,
                "--plugin-config-value",
                "a.b.c=test",
                "a.b.d=one",
                "--plugin-config-value",
                "x.y.z=value",
                "--plugin-config-value",
                "a_dict={key: value}",
                "--plugin-config-value",
                "a_list=[one, two]",
            ]
        )
        settings = group.get_settings(args)

        assert settings["plugin_config"]["a"]["b"]["c"] == "test"
        assert settings["plugin_config"]["a"]["b"]["d"] == "one"
        assert settings["plugin_config"]["x"]["y"]["z"] == "value"
        assert settings["plugin_config"]["a_dict"] == {"key": "value"}
        assert settings["plugin_config"]["a_list"] == ["one", "two"]

    async def test_wallet_key_derivation_method_value_parsing(self):
        key_derivation_method = "key_derivation_method"
        parser = argparse.create_argument_parser()
        group = argparse.WalletGroup()
        group.add_arguments(parser)

        result = parser.parse_args(
            [
                "--wallet-key-derivation-method",
                key_derivation_method,
            ]
        )

        settings = group.get_settings(result)

        assert settings.get("wallet.key_derivation_method") == key_derivation_method

    async def test_wallet_key_value_parsing(self):
        key_value = "some_key_value"
        parser = argparse.create_argument_parser()
        group = argparse.WalletGroup()
        group.add_arguments(parser)

        result = parser.parse_args(
            [
                "--wallet-key",
                key_value,
            ]
        )

        settings = group.get_settings(result)

        assert settings.get("wallet.key") == key_value

    async def test_discover_features_args(self):
        """Test discover features support related argument parsing."""

        parser = argparse.create_argument_parser()
        group = argparse.DiscoverFeaturesGroup()
        group.add_arguments(parser)

        with async_mock.patch.object(parser, "exit") as exit_parser:
            parser.parse_args(["-h"])
            exit_parser.assert_called_once()

        result = parser.parse_args(
            args=(
                "--auto-disclose-features --disclose-features-list"
                " ./aries_cloudagent/config/tests/test_disclose_features_list.yaml"
            )
        )

        assert result.auto_disclose_features
        assert (
            result.disclose_features_list
            == "./aries_cloudagent/config/tests/test_disclose_features_list.yaml"
        )

        settings = group.get_settings(result)

        assert settings.get("auto_disclose_features")
        assert (["test_protocol_1", "test_protocol_2"]) == settings.get(
            "disclose_protocol_list"
        )
        assert (["test_goal_code_1", "test_goal_code_2"]) == settings.get(
            "disclose_goal_code_list"
        )

    def test_universal_resolver(self):
        """Test universal resolver flags."""
        parser = argparse.create_argument_parser()
        group = argparse.GeneralGroup()
        group.add_arguments(parser)

        result = parser.parse_args(["-e", "test", "--universal-resolver"])
        settings = group.get_settings(result)
        endpoint = settings.get("resolver.universal")
        assert endpoint
        assert endpoint == "DEFAULT"

        result = parser.parse_args(
            ["-e", "test", "--universal-resolver", "https://example.com"]
        )
        settings = group.get_settings(result)
        endpoint = settings.get("resolver.universal")
        assert endpoint
        assert endpoint == "https://example.com"

        result = parser.parse_args(
            [
                "-e",
                "test",
                "--universal-resolver",
                "https://example.com",
                "--universal-resolver-regex",
                "regex",
            ]
        )
        settings = group.get_settings(result)
        endpoint = settings.get("resolver.universal")
        assert endpoint
        assert endpoint == "https://example.com"
        supported_regex = settings.get("resolver.universal.supported")
        assert supported_regex
        assert supported_regex == ["regex"]

        result = parser.parse_args(
            ["-e", "test", "--universal-resolver-regex", "regex"]
        )
        with self.assertRaises(argparse.ArgsParseError):
            group.get_settings(result)
