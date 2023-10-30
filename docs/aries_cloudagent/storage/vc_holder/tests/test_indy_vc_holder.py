import pytest
from unittest import mock


from ....config.injection_context import InjectionContext
from ....indy.sdk.profile import IndySdkProfileManager, IndySdkProfile
from ....ledger.indy import IndySdkLedgerPool
from ....wallet.indy import IndySdkWallet

from ..base import VCHolder

from . import test_in_memory_vc_holder as in_memory


async def make_profile():
    key = await IndySdkWallet.generate_wallet_key()
    context = InjectionContext()
    context.injector.bind_instance(IndySdkLedgerPool, IndySdkLedgerPool("name"))

    with mock.patch.object(IndySdkProfile, "_make_finalizer"):
        return await IndySdkProfileManager().provision(
            context,
            {
                "auto_recreate": True,
                "auto_remove": True,
                "name": "test-wallet",
                "key": key,
                "key_derivation_method": "RAW",  # much slower tests with argon-hashed keys
            },
        )


@pytest.fixture()
async def holder():
    profile = await make_profile()
    async with profile.session() as session:
        yield session.inject(VCHolder)
    await profile.close()


@pytest.mark.indy
class TestIndySdkVCHolder(in_memory.TestInMemoryVCHolder):
    # run same test suite with different holder fixture
    pass
