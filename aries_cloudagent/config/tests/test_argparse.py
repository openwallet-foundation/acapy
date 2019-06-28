from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ..argparse import PARSER, get_settings, parse_args


class TestArgParse(AsyncTestCase):
    async def test_parse_settings(self):
        """Test argument parsing."""

        with async_mock.patch.object(PARSER, "exit") as exit_parser:
            parse_args([])
            exit_parser.assert_called_once()

        result = parse_args(
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

        settings = get_settings(result)

        assert settings.get("transport.inbound_configs") == [["http", "0.0.0.0", "80"]]
        assert settings.get("transport.outbound_configs") == ["http"]
