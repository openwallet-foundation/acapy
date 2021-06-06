from configargparse import ArgumentTypeError

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from .. import argparse
from ..error import ArgsParseError
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

    async def test_redis_outbound_queue(self):
        """Test Redis outbound queue connection string."""
        parser = argparse.create_argument_parser()
        group = argparse.TransportGroup()
        group.add_arguments(parser)

        result = parser.parse_args(
            [
                "--inbound-transport",
                "http",
                "0.0.0.0",
                "80",
                "--outbound-queue",
                "redis://test:1234",
            ]
        )

        settings = group.get_settings(result)

        self.assertEqual(settings.get("transport.outbound_queue"), "redis://test:1234")
        self.assertEqual(settings.get("transport.outbound_queue_prefix"), "acapy")
        self.assertEqual(
            settings.get("transport.outbound_queue_class"),
            "aries_cloudagent.transport.outbound.queue.redis:RedisOutboundQueue",
        )

    async def test_redis_outbound_queue_prefix(self):
        """Test Redis outbound queue prefix."""
        parser = argparse.create_argument_parser()
        group = argparse.TransportGroup()
        group.add_arguments(parser)

        result = parser.parse_args(
            [
                "--inbound-transport",
                "http",
                "0.0.0.0",
                "80",
                "--outbound-queue",
                "redis://test:1234",
                "--outbound-queue-prefix",
                "foo",
            ]
        )

        settings = group.get_settings(result)

        self.assertEqual(settings.get("transport.outbound_queue"), "redis://test:1234")
        self.assertEqual(settings.get("transport.outbound_queue_prefix"), "foo")

    async def test_redis_outbound_queue_class(self):
        """Test Redis outbound queue custom class."""
        parser = argparse.create_argument_parser()
        group = argparse.TransportGroup()
        group.add_arguments(parser)

        result = parser.parse_args(
            [
                "--inbound-transport",
                "http",
                "0.0.0.0",
                "80",
                "--outbound-queue",
                "redis://test:1234",
                "--outbound-queue-class",
                "mymodule:MyClass",
            ]
        )

        settings = group.get_settings(result)

        self.assertEqual(settings.get("transport.outbound_queue"), "redis://test:1234")
        self.assertEqual(
            settings.get("transport.outbound_queue_class"), "mymodule:MyClass"
        )

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
