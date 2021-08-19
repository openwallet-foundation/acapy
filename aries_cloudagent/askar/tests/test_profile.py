import pytest

from asynctest import mock as async_mock

from asynctest import TestCase as AsyncTestCase

from .. import profile as test_module
from ...core.profile import Profile, ProfileSession
from ...core.in_memory import InMemoryProfile

class testProfile(AsyncTestCase):
  @pytest.mark.asyncio
  async def test_profile_manager_transaction(self):

    with async_mock.patch(
    "aries_cloudagent.askar.profile.AskarProfile"
    ) as AskarProfile:
      askar_profile = AskarProfile(None, True)
      askar_profile_return = async_mock.MagicMock()
      askar_profile.store.transaction.return_value = askar_profile_return
      askar_profile.context.settings.get.return_value = "walletId"

      sessionProfile = test_module.AskarProfileSession(askar_profile, True)

      assert sessionProfile._opener == askar_profile_return
      askar_profile.context.settings.get.called_once_with("wallet.id")
      askar_profile.store.transaction.called_once_with("walletId")
  
  @pytest.mark.asyncio
  async def test_profile_manager_not_transaction(self):

    with async_mock.patch(
    "aries_cloudagent.askar.profile.AskarProfile"
    ) as AskarProfile:
      askar_profile = AskarProfile(None, False)
      askar_profile_return = async_mock.MagicMock()
      askar_profile.store.session.return_value = askar_profile_return
      askar_profile.context.settings.get.return_value = "walletId"

      sessionProfile = test_module.AskarProfileSession(askar_profile, False)

      assert sessionProfile._opener == askar_profile_return
      askar_profile.context.settings.get.assert_called_with("wallet.id")
      askar_profile.store.session.assert_called_with("walletId")

