
from ..http import Http, HttpSetupError

import pytest
from unittest import mock, TestCase


def func():
    pass


class TestHttp(TestCase):
    good_args = ["0.0.0.0", 80, func]
    bad_args = ["a", "b", "c"]

    web_post_return_value = "web_post_return_value"

    def test_init(self):
        http = Http(*self.good_args)
        assert http.host == self.good_args[0]
        assert http.port == self.good_args[1]
        assert http.message_router == self.good_args[2]

    def test_setup_bad_args(self):
        http = Http(*self.bad_args)
        with self.assertRaises(HttpSetupError) as context:
            http.setup()

        assert "Unable to start webserver" in str(context.exception)

    @mock.patch("indy_catalyst_agent.transport.http.web")
    def test_run_setup(self, mock_aiohttp_web):
        mock_aiohttp_web.Application = mock.MagicMock(auto_spec=True)
        mock_aiohttp_web.post.return_value = self.web_post_return_value
        mock_aiohttp_web.run_app = mock.MagicMock(auto_spec=True)
        mock_aiohttp_web.Application.return_value = mock.MagicMock(auto_spec=True)

        http = Http(*self.good_args)
        http.setup()

        mock_aiohttp_web.Application.assert_called_once_with()
        mock_aiohttp_web.Application.return_value.add_routes.assert_called_once_with(
            [self.web_post_return_value]
        )
        mock_aiohttp_web.run_app.assert_called_once_with(
            mock_aiohttp_web.Application.return_value, host=http.host, port=http.port
        )


# Need to figure out an approach to testing async functions
# async def test_run_parse_message():

#     request = mock.Mock()

#     http = Http(*["0.0.0.0", 80, func])
#     await http.parse_message(request)

#     request.json.assert_called_once_wizh("a")
