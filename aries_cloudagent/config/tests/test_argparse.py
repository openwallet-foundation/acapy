import itertools
from argparse import ArgumentParser, ArgumentTypeError

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from .. import argparse
from ..util import ByteSize


class TestArgParse(AsyncTestCase):
    async def test_groups(self):
        """Test optional argument parsing."""
        parser = ArgumentParser()

        groups = (
            g
            for g in argparse.group.get_registered()
            if g is not argparse.TransportGroup
        )
        argparse.load_argument_groups(parser, *groups)

        parser.parse_args([])

    async def test_transport_settings(self):
        """Test required argument parsing."""

        parser = ArgumentParser()
        group = argparse.TransportGroup()
        group.add_arguments(parser)

        with async_mock.patch.object(parser, "exit") as exit_parser:
            parser.parse_args([])
            exit_parser.assert_called_once()

        result = parser.parse_args(
            [
                "--inbound-transport",
                "http",
                "0.0.0.0",
                "80",
                "--outbound-transport",
                "http",
                "-e",
                "http://default.endpoint/",
                "ws://alternate.endpoint/",
            ]
        )

        assert result.inbound_transports == [["http", "0.0.0.0", "80"]]
        assert result.outbound_transports == ["http"]
        assert result.endpoint == [
            "http://default.endpoint/",
            "ws://alternate.endpoint/",
        ]

        settings = group.get_settings(result)

        assert settings.get("transport.inbound_configs") == [["http", "0.0.0.0", "80"]]
        assert settings.get("transport.outbound_configs") == ["http"]
        assert settings.get("default_endpoint") == "http://default.endpoint/"
        assert settings.get("additional_endpoints") == ["ws://alternate.endpoint/"]

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
