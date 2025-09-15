"""Common test fixtures and data for AnonCreds routes."""

from typing import Any

from ....admin.request_context import AdminRequestContext
from ....tests import mock
from ....utils.testing import create_test_profile
from ...models.revocation import RevRegDef, RevRegDefValue


class BaseAnonCredsRouteTestCase:
    """Base test case with common setup for AnonCreds route tests."""

    async def asyncSetUp(self) -> None:
        """Common test setup for all AnonCreds route tests."""
        self.session_inject = {}
        self.profile = await create_test_profile(
            settings={
                "wallet.type": "askar-anoncreds",
                "admin.admin_api_key": "secret-key",
            },
        )
        self.context = AdminRequestContext.test_context(self.session_inject, self.profile)
        self.request_dict = {
            "context": self.context,
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
            context=self.context,
            headers={"x-api-key": "secret-key"},
        )

        self.test_did = "sample-did"


class BaseAnonCredsRouteTestCaseWithOutbound(BaseAnonCredsRouteTestCase):
    """Base test case with outbound message router for AnonCreds route tests."""

    async def asyncSetUp(self) -> None:
        """Common test setup with outbound message router."""
        await super().asyncSetUp()
        self.request_dict["outbound_message_router"] = mock.CoroutineMock()

        # Update the mock's __getitem__ behavior to handle the new key
        def getitem_side_effect(obj: Any, key: str) -> Any:
            return self.request_dict[key]

        self.request.__getitem__.side_effect = getitem_side_effect


def create_mock_request(context: AdminRequestContext, **kwargs) -> mock.MagicMock:
    """Create a mock request object for testing."""
    request_dict = {"context": context}
    request_dict.update(kwargs)

    return mock.MagicMock(
        app={},
        match_info={},
        query={},
        __getitem__=lambda _, k: request_dict[k],
        context=context,
        headers={"x-api-key": "secret-key"},
    )


def create_standard_rev_reg_def(
    tag: str = "tag",
    cred_def_id: str = "CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
    issuer_id: str = "CsQY9MGeD3CQP4EyuVFo5m",
    max_cred_num: int = 100,
) -> RevRegDef:
    """Create a standard revocation registry definition for testing."""
    return RevRegDef(
        tag=tag,
        cred_def_id=cred_def_id,
        value=RevRegDefValue(
            max_cred_num=max_cred_num,
            public_keys={
                "accum_key": {"z": "1 0BB...386"},
            },
            tails_hash="58NNWYnVxVFzAfUztwGSNBL4551XNq6nXk56pCiKJxxt",
            tails_location="http://tails-server.com",
        ),
        issuer_id=issuer_id,
        type="CL_ACCUM",
    )


def create_standard_rev_reg_def_value(
    max_cred_num: int = 100,
    tails_hash: str = "58NNWYnVxVFzAfUztwGSNBL4551XNq6nXk56pCiKJxxt",
    tails_location: str = "http://tails-server.com",
) -> RevRegDefValue:
    """Create a standard revocation registry definition value for testing."""
    return RevRegDefValue(
        max_cred_num=max_cred_num,
        public_keys={
            "accum_key": {"z": "1 0BB...386"},
        },
        tails_hash=tails_hash,
        tails_location=tails_location,
    )
