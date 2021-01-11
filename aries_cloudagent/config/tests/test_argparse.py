from configargparse import ArgumentTypeError

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from .. import argparse
from ..util import ByteSize


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

        bs = ByteSize(min_size=10)
        with self.assertRaises(ArgumentTypeError):
            bs("5")
        assert bs("12") == 12

        bs = ByteSize(max_size=10)
        with self.assertRaises(ArgumentTypeError):
            bs("15")
        assert bs("10") == 10

        assert repr(bs) == "ByteSize"

    async def test_mediation_x_clear_and_default(self):
        parser = argparse.create_argument_parser()
        group = argparse.MediationGroup()
        group.add_arguments(parser)

        with self.assertRaises(argparse.ArgsParseError):
            args = parser.parse_args(
                ["--clear-default-mediator", "--default-mediator-id", "asdf"]
            )
            group.get_settings(args)
