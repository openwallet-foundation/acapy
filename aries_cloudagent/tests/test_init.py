# import aries_cloudagent

# from unittest import mock
# from asynctest import TestCase as AsyncTestCase
# from asynctest import mock as async_mock


# class TestAsyncMain(AsyncTestCase):

#     parsed_transports = [["a", "b", "c"]]
#     transport_arg_value = "transport"
#     host_arg_value = "host"
#     port_arg_value = "port"

#     @mock.patch("aries_cloudagent.asyncio", autospec=True)
#     @mock.patch("aries_cloudagent.LoggingConfigurator", autospec=True)
#     @mock.patch("aries_cloudagent.parser.parse_args", autospec=True)
#     @mock.patch("aries_cloudagent.Conductor", autospec=True)
#     @mock.patch("aries_cloudagent.start", autospec=True)
#     def test_main_parse(
#         self,
#         mock_start,
#         mock_conductor,
#         mock_parse_args,
#         mock_logging_configurator,
#         mock_asyncio,
#     ):
#         type(mock_parse_args.return_value).transports = self.parsed_transports
#         aries_cloudagent.main()

#         mock_parse_args.assert_called_once()
#         mock_start.assert_called_once_with(
#             [
#                 {
#                     "transport": self.parsed_transports[0][0],
#                     "host": self.parsed_transports[0][1],
#                     "port": self.parsed_transports[0][2],
#                 }
#             ]
#         )

#     @async_mock.patch("aries_cloudagent.Conductor", autospec=True)
#     async def test_main(self, mock_conductor):
#         await aries_cloudagent.start(self.parsed_transports)

#         mock_conductor.assert_called_once_with(self.parsed_transports)
#         mock_conductor.return_value.start.assert_called_once_with()
