from argparse import ArgumentParser

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ..argparse import TransportGroup


class TestArgParse(AsyncTestCase):
    async def test_transport_settings(self):
        """Test argument parsing."""

        parser = ArgumentParser()
        group = TransportGroup()
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
            ]
        )

        assert result.inbound_transports == [["http", "0.0.0.0", "80"]]
        assert result.outbound_transports == ["http"]

        settings = group.get_settings(result)

        assert settings.get("transport.inbound_configs") == [["http", "0.0.0.0", "80"]]
        assert settings.get("transport.outbound_configs") == ["http"]
