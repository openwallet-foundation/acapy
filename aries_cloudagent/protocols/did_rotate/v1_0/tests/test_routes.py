import unittest
from unittest import IsolatedAsyncioTestCase

from .....admin.request_context import AdminRequestContext
from .....protocols.didcomm_prefix import DIDCommPrefix
from .....storage.error import StorageNotFoundError
from .....tests import mock
from ..messages import Hangup, Rotate
from .. import message_types as test_message_types
from .. import routes as test_module
from ..tests import MockConnRecord, test_conn_id

test_valid_rotate_request = {
    "to_did": "did:example:newdid",
}


def generate_mock_hangup_message():
    msg = Hangup(_id="test-message-id")
    return msg


def generate_mock_rotate_message():
    msg = Rotate(_id="test-message-id", **test_valid_rotate_request)
    return msg


class TestDIDRotateRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session_inject = {}

        self.context = AdminRequestContext.test_context(self.session_inject)
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": mock.CoroutineMock(),
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

    @mock.patch.object(
        test_module.ConnRecord,
        "retrieve_by_id",
        return_value=MockConnRecord(test_conn_id, True),
    )
    @mock.patch.object(
        test_module,
        "DIDRotateManager",
        autospec=True,
        return_value=mock.MagicMock(
            rotate_my_did=mock.CoroutineMock(
                return_value=generate_mock_rotate_message()
            )
        ),
    )
    async def test_rotate(self, *_):
        self.request.match_info = {"conn_id": test_conn_id}
        self.request.json = mock.CoroutineMock(return_value=test_valid_rotate_request)

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            await test_module.rotate(self.request)

            mock_response.assert_called_once_with(
                {
                    "@id": "test-message-id",
                    "@type": DIDCommPrefix.NEW.value + "/" + test_message_types.ROTATE,
                    **test_valid_rotate_request,
                }
            )

    @mock.patch.object(
        test_module.ConnRecord,
        "retrieve_by_id",
        return_value=MockConnRecord(test_conn_id, True),
    )
    @mock.patch.object(
        test_module,
        "DIDRotateManager",
        autospec=True,
        return_value=mock.MagicMock(
            hangup=mock.CoroutineMock(return_value=generate_mock_hangup_message())
        ),
    )
    async def test_hangup(self, *_):
        self.request.match_info = {"conn_id": test_conn_id}
        self.request.json = mock.CoroutineMock(return_value=test_valid_rotate_request)

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            await test_module.hangup(self.request)

            mock_response.assert_called_once_with(
                {
                    "@id": "test-message-id",
                    "@type": DIDCommPrefix.NEW.value + "/" + test_message_types.HANGUP,
                }
            )

    async def test_rotate_conn_not_found(self):
        self.request.match_info = {"conn_id": test_conn_id}
        self.request.json = mock.CoroutineMock(return_value=test_valid_rotate_request)

        with mock.patch.object(
            test_module.ConnRecord,
            "retrieve_by_id",
            mock.CoroutineMock(side_effect=StorageNotFoundError()),
        ) as mock_retrieve_by_id:

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.rotate(self.request)


if __name__ == "__main__":
    unittest.main()
