"""Test VC routes."""

from unittest import IsolatedAsyncioTestCase

from ...admin.request_context import AdminRequestContext
from ...tests import mock
from ...utils.testing import create_test_profile
from .. import routes as test_module
from ..vc_ld.manager import VcLdpManager, VcLdpManagerError


class TestVCRoutes(IsolatedAsyncioTestCase):
    """Test VC routes."""

    async def asyncSetUp(self):
        """Set up test dependencies."""
        self.profile = await create_test_profile(
            settings={"admin.admin_api_key": "secret-key"},
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

        # Sample credential for testing
        self.sample_credential = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            "id": "http://example.edu/credentials/3732",
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuer": "did:example:123",
            "issuanceDate": "2020-03-10T04:24:12.164Z",
            "credentialSubject": {
                "id": "did:example:456",
                "degree": {
                    "type": "BachelorDegree",
                    "name": "Bachelor of Science and Arts",
                },
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "created": "2020-03-10T04:24:12.164Z",
                "proofPurpose": "assertionMethod",
                "verificationMethod": "did:example:123#key-1",
                "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..",
            },
        }

    async def test_store_credential_with_verification(self):
        """Test storing a credential with verification (default behavior)."""
        self.request.json = mock.CoroutineMock(
            return_value={
                "verifiableCredential": self.sample_credential,
            }
        )

        with mock.patch.object(
            test_module, "VcLdpManager", autospec=True
        ) as mock_mgr_cls:
            mock_mgr = mock.MagicMock(spec=VcLdpManager)
            mock_mgr_cls.return_value = mock_mgr
            mock_mgr.verify_credential = mock.CoroutineMock()
            mock_mgr.store_credential = mock.CoroutineMock()

            result = await test_module.store_credential_route(self.request)

            # Verify that verification was called
            mock_mgr.verify_credential.assert_called_once()
            mock_mgr.store_credential.assert_called_once()

            assert result.status == 200

    async def test_store_credential_skip_verification_false(self):
        """Test storing credential with skip_verification explicitly set to False."""
        self.request.json = mock.CoroutineMock(
            return_value={
                "verifiableCredential": self.sample_credential,
                "options": {"skipVerification": False},
            }
        )

        with mock.patch.object(
            test_module, "VcLdpManager", autospec=True
        ) as mock_mgr_cls:
            mock_mgr = mock.MagicMock(spec=VcLdpManager)
            mock_mgr_cls.return_value = mock_mgr
            mock_mgr.verify_credential = mock.CoroutineMock()
            mock_mgr.store_credential = mock.CoroutineMock()

            result = await test_module.store_credential_route(self.request)

            # Verify that verification was called
            mock_mgr.verify_credential.assert_called_once()
            mock_mgr.store_credential.assert_called_once()

            assert result.status == 200

    async def test_store_credential_skip_verification_true(self):
        """Test storing credential without verification when skip_verification is True."""
        self.request.json = mock.CoroutineMock(
            return_value={
                "verifiableCredential": self.sample_credential,
                "options": {"skipVerification": True},
            }
        )

        with mock.patch.object(
            test_module, "VcLdpManager", autospec=True
        ) as mock_mgr_cls:
            mock_mgr = mock.MagicMock(spec=VcLdpManager)
            mock_mgr_cls.return_value = mock_mgr
            mock_mgr.verify_credential = mock.CoroutineMock()
            mock_mgr.store_credential = mock.CoroutineMock()

            result = await test_module.store_credential_route(self.request)

            # Verify that verification was NOT called
            mock_mgr.verify_credential.assert_not_called()
            # But storage was called
            mock_mgr.store_credential.assert_called_once()

            assert result.status == 200

    async def test_store_credential_with_invalid_proof(self):
        """Test that verification errors are handled when skip_verification is False."""
        self.request.json = mock.CoroutineMock(
            return_value={
                "verifiableCredential": self.sample_credential,
                "options": {"skipVerification": False},
            }
        )

        with mock.patch.object(
            test_module, "VcLdpManager", autospec=True
        ) as mock_mgr_cls:
            mock_mgr = mock.MagicMock(spec=VcLdpManager)
            mock_mgr_cls.return_value = mock_mgr
            mock_mgr.verify_credential = mock.CoroutineMock(
                side_effect=VcLdpManagerError("Invalid proof")
            )
            mock_mgr.store_credential = mock.CoroutineMock()

            result = await test_module.store_credential_route(self.request)

            # Should return error
            assert result.status == 400
            # Store should not be called
            mock_mgr.store_credential.assert_not_called()

    async def test_store_credential_skip_verification_allows_invalid_proof(self):
        """Test that invalid proofs can be stored when skip_verification is True."""
        self.request.json = mock.CoroutineMock(
            return_value={
                "verifiableCredential": self.sample_credential,
                "options": {"skipVerification": True},
            }
        )

        with mock.patch.object(
            test_module, "VcLdpManager", autospec=True
        ) as mock_mgr_cls:
            mock_mgr = mock.MagicMock(spec=VcLdpManager)
            mock_mgr_cls.return_value = mock_mgr
            # Even if verify_credential would fail, it shouldn't be called
            mock_mgr.verify_credential = mock.CoroutineMock(
                side_effect=VcLdpManagerError("Invalid proof")
            )
            mock_mgr.store_credential = mock.CoroutineMock()

            result = await test_module.store_credential_route(self.request)

            # Verification was skipped, so no error
            mock_mgr.verify_credential.assert_not_called()
            # Storage was successful
            mock_mgr.store_credential.assert_called_once()

            assert result.status == 200
