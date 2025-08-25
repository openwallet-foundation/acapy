import os
import shutil
from unittest import IsolatedAsyncioTestCase

import pytest

from ....admin.request_context import AdminRequestContext
from ....revocation import routes as test_module
from ....tests import mock
from ....utils.testing import create_test_profile


class TestRevocationRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile(
            settings={
                "admin.admin_api_key": "secret-key",
                "wallet.type": "askar-anoncreds",
            },
        )
        self.context = AdminRequestContext.test_context({}, self.profile)
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": mock.CoroutineMock(),
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "secret-key"},
        )

        self.test_did = "sample-did"

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(
            _state={
                "swagger_dict": {
                    "paths": {
                        "/revocation/registry/{rev_reg_id}/tails-file": {
                            "get": {"responses": {"200": {"description": "tails file"}}}
                        }
                    }
                }
            }
        )
        test_module.post_process_routes(mock_app)
        assert mock_app._state["swagger_dict"]["paths"][
            "/revocation/registry/{rev_reg_id}/tails-file"
        ]["get"]["responses"]["200"]["schema"] == {"type": "string", "format": "binary"}

        assert "tags" in mock_app._state["swagger_dict"]


class TestDeleteTails(IsolatedAsyncioTestCase):
    def setUp(self):
        self.rev_reg_id = "rev_reg_id_123"
        self.cred_def_id = "cred_def_id_456"

        self.main_dir_rev = "path/to/main/dir/rev"
        self.tails_path = os.path.join(self.main_dir_rev, "tails")
        if not (os.path.exists(self.main_dir_rev)):
            os.makedirs(self.main_dir_rev)
        open(self.tails_path, "w").close()

    @pytest.mark.xfail(reason="This test never worked but was skipped due to a bug")
    async def test_delete_tails_by_rev_reg_id(self):
        # Setup
        rev_reg_id = self.rev_reg_id

        # Test
        result = await test_module.delete_tails(
            {"context": None, "query": {"rev_reg_id": rev_reg_id}}
        )

        # Assert
        self.assertEqual(result, {"message": "All files deleted successfully"})
        self.assertFalse(os.path.exists(self.tails_path))

    @pytest.mark.xfail(reason="This test never worked but was skipped due to a bug")
    async def test_delete_tails_by_cred_def_id(self):
        # Setup
        cred_def_id = self.cred_def_id
        main_dir_cred = "path/to/main/dir/cred"
        os.makedirs(main_dir_cred)
        cred_dir = os.path.join(main_dir_cred, cred_def_id)
        os.makedirs(cred_dir)

        # Test
        result = await test_module.delete_tails(
            {"context": None, "query": {"cred_def_id": cred_def_id}}
        )

        # Assert
        self.assertEqual(result, {"message": "All files deleted successfully"})
        self.assertFalse(os.path.exists(cred_dir))
        self.assertTrue(os.path.exists(main_dir_cred))

    @pytest.mark.xfail(reason="This test never worked but was skipped due to a bug")
    async def test_delete_tails_not_found(self):
        # Setup
        cred_def_id = "invalid_cred_def_id"

        # Test
        result = await test_module.delete_tails(
            {"context": None, "query": {"cred_def_id": cred_def_id}}
        )

        # Assert
        self.assertEqual(result, {"message": "No such file or directory"})
        self.assertTrue(os.path.exists(self.main_dir_rev))

    def tearDown(self):
        if os.path.exists(self.main_dir_rev):
            shutil.rmtree(self.main_dir_rev)
