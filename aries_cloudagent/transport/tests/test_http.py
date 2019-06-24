# import json

# from ..http import Http, HttpSetupError, InvalidMessageError

# import pytest
# from unittest import mock, TestCase

# from asynctest import TestCase as AsyncTestCase
# from asynctest import mock as async_mock
# from asynctest import patch as async_patch


# def func():
#     pass


# class TestHttp(TestCase):
#     good_args = ["0.0.0.0", 80, func]

#     def test_init(self):
#         http = Http(*self.good_args)
#         assert http.host == self.good_args[0]
#         assert http.port == self.good_args[1]
#         assert http.message_router == self.good_args[2]


# class TestAsyncHttp(AsyncTestCase):
#     good_args = ["0.0.0.0", 80, func]
#     bad_args = ["a", "b", "c"]
#     web_post_return_value = "web_post_return_value"

#     async def test_run_parse_message(self):
#         request = async_mock.MagicMock()
#         request.json = async_mock.CoroutineMock()
#         http = Http(*["0.0.0.0", 80, func])
#         result = await http.parse_message(request)
#         request.json.assert_called_once_with()
#         assert result is request.json.return_value

#     async def test_run_parse_bad_message(self):
#         request = async_mock.MagicMock()
#         request.json = async_mock.CoroutineMock(
#             side_effect=json.JSONDecodeError("", "{}", 1)
#         )
#         http = Http(*["0.0.0.0", 80, func])

#         with self.assertRaises(InvalidMessageError) as context:
#             await http.parse_message(request)
#         assert (
#             str(context.exception)
#             == "Request body must contain a valid application/json payload"
#         )

#     async def test_setup_bad_args(self):
#         http = Http(*self.bad_args)
#         with self.assertRaises(HttpSetupError) as context:
#             await http.start()

#         assert "Unable to start webserver" in str(context.exception)

#     @async_mock.patch("aries_cloudagent.transport.http.web")
#     async def test_run_setup(self, mock_aiohttp_web):
#         mock_aiohttp_web.Application = mock.MagicMock(auto_spec=True)
#         mock_aiohttp_web.post.return_value = self.web_post_return_value
#         mock_aiohttp_web.run_app = mock.MagicMock(auto_spec=True)
#         mock_aiohttp_web.Application.return_value = mock.MagicMock(auto_spec=True)
#         mock_aiohttp_web.AppRunner = mock.MagicMock(auto_spec=True)
#         mock_aiohttp_web.AppRunner.return_value.setup = async_mock.CoroutineMock(
#             auto_spec=True
#         )
#         mock_aiohttp_web.TCPSite = mock.MagicMock(auto_spec=True)
#         mock_aiohttp_web.TCPSite.return_value.start = async_mock.CoroutineMock(
#             auto_spec=True
#         )

#         http = Http(*self.good_args)
#         await http.start()

#         mock_aiohttp_web.Application.assert_called_once_with()
#         mock_aiohttp_web.Application.return_value.add_routes.assert_called_once_with(
#             [self.web_post_return_value]
#         )

#         mock_aiohttp_web.TCPSite.assert_called_once_with(
#             mock_aiohttp_web.AppRunner.return_value, host=http.host, port=http.port
#         )
#         mock_aiohttp_web.TCPSite.return_value.start.assert_called_once_with()

#     @async_mock.patch("aries_cloudagent.transport.http.web.Response")
#     async def test_run_message_handler(self, mock_web_response):
#         request = async_mock.CoroutineMock()
#         http = Http(*["0.0.0.0", 80, func])

#         http.parse_message = async_mock.CoroutineMock()
#         http.message_router = async_mock.MagicMock()

#         await http.message_handler(request)

#         mock_web_response.assert_called_once_with(text="OK", status=200)

#         http.parse_message.assert_called_once_with(request)

#     @async_mock.patch("aries_cloudagent.transport.http.web.Response")
#     async def test_run_message_handler_fail(self, mock_web_response):
#         request = async_mock.CoroutineMock()
#         http = Http(*["0.0.0.0", 80, func])

#         http.parse_message = async_mock.CoroutineMock()

#         err_str = "err123"

#         http.message_router = async_mock.MagicMock(side_effect=Exception(err_str))

#         await http.message_handler(request)

#         mock_web_response.assert_called_once_with(text=err_str, status=400)

#         http.parse_message.assert_called_once_with(request)
