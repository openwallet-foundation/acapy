from unittest import IsolatedAsyncioTestCase

import pytest
from aries_askar import AskarError, AskarErrorCode

from acapy_agent.indy.credx.holder import CredxError, IndyHolderError
from acapy_agent.utils.testing import create_test_profile

from ....tests import mock
from .. import holder


@pytest.mark.askar
@pytest.mark.indy_credx
class TestIndyCredxGetLinkSecret(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.holder_profile = await create_test_profile()
        self.holder = holder.IndyCredxHolder(self.holder_profile)

        self.mock_session = mock.MagicMock()
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None
        self.holder._profile.session = mock.MagicMock(return_value=self.mock_session)

    @mock.patch("acapy_agent.indy.credx.holder.LinkSecret.load")
    @mock.patch("acapy_agent.indy.credx.holder.LinkSecret.create")
    async def test_get_link_secret_existing(self, mock_create, mock_load):
        # Mock session and record
        mock_record = mock.MagicMock()
        mock_record.raw_value = b'{"value": {"ms": "mocked_ms"}}'

        self.mock_session.handle.fetch = mock.CoroutineMock(return_value=mock_record)

        # Test fetching existing link secret
        secret = await self.holder.get_link_secret()
        assert secret is not None
        mock_load.assert_called_once_with(mock_record.raw_value)
        mock_create.assert_not_called()

    @mock.patch("acapy_agent.indy.credx.holder.LinkSecret.load")
    async def test_get_link_secret_fetch_error(self, mock_load):
        # Mock session to raise an error
        self.mock_session.handle.fetch = mock.CoroutineMock(
            side_effect=AskarError(AskarErrorCode.BACKEND, "Fetch error")
        )

        with pytest.raises(IndyHolderError, match="Error fetching link secret"):
            await self.holder.get_link_secret()

        mock_load.assert_not_called()

    @mock.patch("acapy_agent.indy.credx.holder.LinkSecret.load")
    async def test_get_link_secret_load_error(self, mock_load):
        # Mock session and record
        mock_record = mock.MagicMock()
        mock_record.raw_value = b'{"value": {"ms": "mocked_ms"}}'
        self.mock_session.handle.fetch = mock.CoroutineMock(return_value=mock_record)

        # Mock load to raise an error
        mock_load.side_effect = CredxError(4, "Load error")

        with pytest.raises(IndyHolderError, match="Error loading link secret"):
            await self.holder.get_link_secret()

    @mock.patch("acapy_agent.indy.credx.holder.LinkSecret.load")
    async def test_get_link_secret_fallback_load(self, mock_load):
        # Mock session and record
        mock_record = mock.MagicMock()
        mock_record.raw_value = b'{"value": {"ms": "mocked_ms"}}'
        self.mock_session.handle.fetch = mock.CoroutineMock(return_value=mock_record)

        # Mock load to raise an error initially
        mock_load.side_effect = [CredxError(4, "Load error"), mock.MagicMock()]

        # Test fallback method
        secret = await self.holder.get_link_secret()
        assert secret is not None
        assert mock_load.call_count == 2

    @mock.patch("acapy_agent.indy.credx.holder.LinkSecret.create")
    async def test_get_link_secret_create_error(self, mock_create):
        # Mock session to return no record
        self.mock_session.handle.fetch = mock.CoroutineMock(return_value=None)

        # Mock create to raise an error
        mock_create.side_effect = CredxError(4, "Create error")

        with pytest.raises(IndyHolderError, match="Error creating link secret"):
            await self.holder.get_link_secret()

    @mock.patch("acapy_agent.indy.credx.holder.LinkSecret.create")
    async def test_get_link_secret_create_and_save(self, mock_create):
        # Mock session to return no record
        self.mock_session.handle.fetch = mock.CoroutineMock(return_value=None)

        # Mock successful creation
        mock_secret = mock.MagicMock()
        mock_create.return_value = mock_secret

        # Mock successful insert
        self.mock_session.handle.insert = mock.CoroutineMock()

        # Test creating and saving new link secret
        secret = await self.holder.get_link_secret()
        assert secret is not None
        mock_create.assert_called_once()
        self.mock_session.handle.insert.assert_called_once()

    @mock.patch("acapy_agent.indy.credx.holder.LinkSecret.create")
    async def test_get_link_secret_duplicate_error(self, mock_create):
        # Mock session to return no record
        self.mock_session.handle.fetch = mock.CoroutineMock(return_value=None)

        # Mock successful creation
        mock_secret = mock.MagicMock()
        mock_create.return_value = mock_secret

        # Mock insert to raise a duplicate error
        self.mock_session.handle.insert = mock.CoroutineMock(
            side_effect=[
                AskarError(AskarErrorCode.DUPLICATE, "Duplicate error"),
                mock.CoroutineMock(),
            ]
        )

        # Test handling of duplicate error
        secret = await self.holder.get_link_secret()
        assert secret is not None
        assert mock_create.call_count == 2
        assert self.mock_session.handle.insert.call_count == 2
