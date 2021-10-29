import asyncio
import json

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from copy import deepcopy

from collections import OrderedDict

from ....cache.base import BaseCache
from ....cache.in_memory import InMemoryCache
from ....core.in_memory import InMemoryProfile
from ....messaging.responder import BaseResponder

from ...error import LedgerError
from ...indy_vdr import IndyVdrLedger, IndyVdrLedgerPool
from ...merkel_validation.tests.test_data import GET_NYM_REPLY

from .. import indy_vdr_manager as test_module
from ..base_manager import MultipleLedgerManagerError
from ..indy_vdr_manager import MultiIndyVDRLedgerManager


class TestMultiIndyVDRLedgerManager(AsyncTestCase):
    async def setUp(self):
        self.profile = InMemoryProfile.test_profile(bind={BaseCache: InMemoryCache()})
        self.context = self.profile.context
        setattr(self.context, "profile", self.profile)
        self.responder = async_mock.CoroutineMock(send=async_mock.CoroutineMock())
        self.context.injector.bind_instance(BaseResponder, self.responder)
        self.production_ledger = OrderedDict()
        self.non_production_ledger = OrderedDict()
        self.production_ledger["test_prod_1"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_prod_1"), self.profile
        )
        self.production_ledger["test_prod_2"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_prod_2"), self.profile
        )
        self.non_production_ledger["test_non_prod_1"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_non_prod_1"), self.profile
        )
        self.non_production_ledger["test_non_prod_2"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_non_prod_2"), self.profile
        )
        self.manager = MultiIndyVDRLedgerManager(
            self.profile,
            production_ledgers=self.production_ledger,
            non_production_ledgers=self.non_production_ledger,
        )

    async def test_get_write_ledger_prod_ledger(self):
        ledger_id, ledger_inst = await self.manager.get_write_ledger()
        assert ledger_id == "test_prod_1"
        assert ledger_inst.pool.name == "test_prod_1"

    async def test_get_write_ledger_non_prod_ledger(self):
        self.non_production_ledger = OrderedDict()
        self.non_production_ledger["test_non_prod_1"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_non_prod_1"), self.profile
        )
        self.non_production_ledger["test_non_prod_2"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_non_prod_2"), self.profile
        )
        self.manager = MultiIndyVDRLedgerManager(
            self.profile,
            non_production_ledgers=self.non_production_ledger,
        )
        ledger_id, ledger_inst = await self.manager.get_write_ledger()
        assert ledger_id == "test_non_prod_1"
        assert ledger_inst.pool.name == "test_non_prod_1"

    async def test_set_write_ledger_prod_ledger(self):
        await self.manager.set_write_ledger("test_prod_1")
        write_ledger_info = self.manager.write_ledger_info
        assert write_ledger_info[0] == "test_prod_1"
        assert write_ledger_info[1].pool.name == "test_prod_1"

    async def test_set_write_ledger_non_prod_ledger(self):
        self.non_production_ledger = OrderedDict()
        self.non_production_ledger["test_non_prod_1"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_non_prod_1"), self.profile
        )
        self.non_production_ledger["test_non_prod_2"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_non_prod_2"), self.profile
        )
        self.manager = MultiIndyVDRLedgerManager(
            self.profile,
            non_production_ledgers=self.non_production_ledger,
        )
        await self.manager.set_write_ledger("test_non_prod_1")
        write_ledger_info = self.manager.write_ledger_info
        assert write_ledger_info[0] == "test_non_prod_1"
        assert write_ledger_info[1].pool.name == "test_non_prod_1"

    async def test_set_write_ledger_x(self):
        with self.assertRaises(MultipleLedgerManagerError) as cm:
            await self.manager.set_write_ledger("test_prod_invalid")
            assert (
                "not found in configured production and non_production ledgers." in cm
            )

    async def test_reset_write_ledger(self):
        ledger_id, ledger_inst = await self.manager.reset_write_ledger()
        assert ledger_id == "test_prod_1"
        assert ledger_inst.pool.name == "test_prod_1"

    async def test_update_ledger_config(self):
        # production
        ledger_config_list = [
            {
                "id": "updated_test_prod_1",
                "pool_name": "updated_pool_name",
                "is_production": True,
                "genesis_transactions": "genesis_transactions",
            }
        ]
        await self.manager.update_ledger_config(ledger_config_list)
        assert len(self.manager.production_ledgers) == 1
        assert len(self.manager.non_production_ledgers) == 0
        assert "updated_test_prod_1" in self.manager.production_ledgers
        assert (
            self.manager.production_ledgers["updated_test_prod_1"]
        ).pool.name == "updated_pool_name"
        # non production
        ledger_config_list = [
            {
                "id": "updated_test_non_prod_1",
                "pool_name": "updated_pool_name",
                "is_production": False,
                "genesis_transactions": "genesis_transactions",
            }
        ]
        await self.manager.update_ledger_config(ledger_config_list)
        assert len(self.manager.production_ledgers) == 0
        assert len(self.manager.non_production_ledgers) == 1
        assert "updated_test_non_prod_1" in self.manager.non_production_ledgers
        assert (
            self.manager.non_production_ledgers["updated_test_non_prod_1"]
        ).pool.name == "updated_pool_name"

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_get_ledger_by_did_self_cert_a(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        with async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait:
            mock_build_get_nym_req.return_value = async_mock.MagicMock()
            mock_submit.return_value = json.dumps(GET_NYM_REPLY)
            mock_wait.return_value = mock_submit.return_value
            (
                ledger_id,
                ledger_inst,
                is_self_certified,
            ) = await self.manager._get_ledger_by_did(
                "test_prod_1", "Av63wJYM7xYR4AiygYq4c3"
            )
            assert ledger_id == "test_prod_1"
            assert ledger_inst.pool.name == "test_prod_1"
            assert is_self_certified

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_get_ledger_by_did_self_cert_b(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        self.non_production_ledger = OrderedDict()
        self.non_production_ledger["test_non_prod_1"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_non_prod_1"), self.profile
        )
        self.non_production_ledger["test_non_prod_2"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_non_prod_2"), self.profile
        )
        self.manager = MultiIndyVDRLedgerManager(
            self.profile,
            non_production_ledgers=self.non_production_ledger,
        )
        with async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait:
            mock_build_get_nym_req.return_value = async_mock.MagicMock()
            mock_submit.return_value = json.dumps(GET_NYM_REPLY)
            mock_wait.return_value = mock_submit.return_value
            (
                ledger_id,
                ledger_inst,
                is_self_certified,
            ) = await self.manager._get_ledger_by_did(
                "test_non_prod_1", "Av63wJYM7xYR4AiygYq4c3"
            )
            assert ledger_id == "test_non_prod_1"
            assert ledger_inst.pool.name == "test_non_prod_1"
            assert is_self_certified

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_get_ledger_by_did_not_self_cert(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        get_nym_reply = deepcopy(GET_NYM_REPLY)
        get_nym_reply["result"]["data"]["verkey"] = "ABUF7uxYTxZ6qYdZ4G9e1Gi"
        with async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            test_module.SubTrie, "verify_spv_proof", async_mock.CoroutineMock()
        ) as mock_verify_spv_proof:
            mock_build_get_nym_req.return_value = async_mock.MagicMock()
            mock_submit.return_value = json.dumps(get_nym_reply)
            mock_wait.return_value = mock_submit.return_value
            mock_verify_spv_proof.return_value = True
            (
                ledger_id,
                ledger_inst,
                is_self_certified,
            ) = await self.manager._get_ledger_by_did(
                "test_prod_1", "Av63wJYM7xYR4AiygYq4c3"
            )
            assert ledger_id == "test_prod_1"
            assert ledger_inst.pool.name == "test_prod_1"
            assert not is_self_certified

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_get_ledger_by_did_state_proof_not_valid(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        get_nym_reply = deepcopy(GET_NYM_REPLY)
        get_nym_reply["result"]["data"]["verkey"] = "ABUF7uxYTxZ6qYdZ4G9e1Gi"
        with async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait:
            mock_build_get_nym_req.return_value = async_mock.MagicMock()
            mock_submit.return_value = json.dumps(get_nym_reply)
            mock_wait.return_value = mock_submit.return_value
            assert not await self.manager._get_ledger_by_did(
                "test_prod_1", "Av63wJYM7xYR4AiygYq4c3"
            )

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_get_ledger_by_did_no_data(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        get_nym_reply = deepcopy(GET_NYM_REPLY)
        get_nym_reply.get("result").pop("data")
        with async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait:
            mock_build_get_nym_req.return_value = async_mock.MagicMock()
            mock_submit.return_value = json.dumps(get_nym_reply)
            mock_wait.return_value = mock_submit.return_value
            assert not await self.manager._get_ledger_by_did(
                "test_prod_1", "Av63wJYM7xYR4AiygYq4c3"
            )

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_get_ledger_by_did_timeout(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        mock_build_get_nym_req.return_value = async_mock.MagicMock()
        mock_submit.side_effect = asyncio.TimeoutError
        assert not await self.manager._get_ledger_by_did(
            "test_prod_1", "Av63wJYM7xYR4AiygYq4c3"
        )

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_get_ledger_by_did_ledger_error(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        mock_build_get_nym_req.return_value = async_mock.MagicMock()
        mock_submit.side_effect = LedgerError
        assert not await self.manager._get_ledger_by_did(
            "test_prod_1", "Av63wJYM7xYR4AiygYq4c3"
        )

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_lookup_did_in_configured_ledgers_self_cert_prod(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        with async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait:
            mock_build_get_nym_req.return_value = async_mock.MagicMock()
            mock_submit.return_value = json.dumps(GET_NYM_REPLY)
            mock_wait.return_value = mock_submit.return_value
            (
                ledger_id,
                ledger_inst,
            ) = await self.manager.lookup_did_in_configured_ledgers(
                "Av63wJYM7xYR4AiygYq4c3", cache_did=True
            )
            assert ledger_id == "test_prod_1"
            assert ledger_inst.pool.name == "test_prod_1"

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_get_ledger_by_did_not_self_cert_not_self_cert_prod(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        get_nym_reply = deepcopy(GET_NYM_REPLY)
        get_nym_reply["result"]["data"]["verkey"] = "ABUF7uxYTxZ6qYdZ4G9e1Gi"
        with async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            test_module.SubTrie, "verify_spv_proof", async_mock.CoroutineMock()
        ) as mock_verify_spv_proof:
            mock_build_get_nym_req.return_value = async_mock.MagicMock()
            mock_submit.return_value = json.dumps(get_nym_reply)
            mock_wait.return_value = mock_submit.return_value
            mock_verify_spv_proof.return_value = True
            (
                ledger_id,
                ledger_inst,
            ) = await self.manager.lookup_did_in_configured_ledgers(
                "Av63wJYM7xYR4AiygYq4c3", cache_did=True
            )
            assert ledger_id == "test_prod_1"
            assert ledger_inst.pool.name == "test_prod_1"

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_lookup_did_in_configured_ledgers_self_cert_non_prod(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        self.non_production_ledger = OrderedDict()
        self.non_production_ledger["test_non_prod_1"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_non_prod_1"), self.profile
        )
        self.non_production_ledger["test_non_prod_2"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_non_prod_2"), self.profile
        )
        self.manager = MultiIndyVDRLedgerManager(
            self.profile,
            non_production_ledgers=self.non_production_ledger,
        )
        with async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait:
            mock_build_get_nym_req.return_value = async_mock.MagicMock()
            mock_submit.return_value = json.dumps(GET_NYM_REPLY)
            mock_wait.return_value = mock_submit.return_value
            (
                ledger_id,
                ledger_inst,
            ) = await self.manager.lookup_did_in_configured_ledgers(
                "Av63wJYM7xYR4AiygYq4c3", cache_did=True
            )
            assert ledger_id == "test_non_prod_1"
            assert ledger_inst.pool.name == "test_non_prod_1"

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_get_ledger_by_did_not_self_cert_not_self_cert_non_prod(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        self.non_production_ledger = OrderedDict()
        self.non_production_ledger["test_non_prod_1"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_non_prod_1"), self.profile
        )
        self.non_production_ledger["test_non_prod_2"] = IndyVdrLedger(
            IndyVdrLedgerPool("test_non_prod_2"), self.profile
        )
        self.manager = MultiIndyVDRLedgerManager(
            self.profile,
            non_production_ledgers=self.non_production_ledger,
        )
        get_nym_reply = deepcopy(GET_NYM_REPLY)
        get_nym_reply["result"]["data"]["verkey"] = "ABUF7uxYTxZ6qYdZ4G9e1Gi"
        with async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            test_module.SubTrie, "verify_spv_proof", async_mock.CoroutineMock()
        ) as mock_verify_spv_proof:
            mock_build_get_nym_req.return_value = async_mock.MagicMock()
            mock_submit.return_value = json.dumps(get_nym_reply)
            mock_wait.return_value = mock_submit.return_value
            mock_verify_spv_proof.return_value = True
            (
                ledger_id,
                ledger_inst,
            ) = await self.manager.lookup_did_in_configured_ledgers(
                "Av63wJYM7xYR4AiygYq4c3", cache_did=True
            )
            assert ledger_id == "test_non_prod_1"
            assert ledger_inst.pool.name == "test_non_prod_1"

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_lookup_did_in_configured_ledgers_x(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        with async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            test_module.SubTrie, "verify_spv_proof", async_mock.CoroutineMock()
        ) as mock_verify_spv_proof:
            mock_build_get_nym_req.return_value = async_mock.MagicMock()
            mock_submit.return_value = json.dumps(GET_NYM_REPLY)
            mock_wait.return_value = mock_submit.return_value
            mock_verify_spv_proof.return_value = False
            with self.assertRaises(MultipleLedgerManagerError) as cm:
                await self.manager.lookup_did_in_configured_ledgers(
                    "Av63wJYM7xYR4AiygYq4c3", cache_did=True
                )
                assert "not found in any of the ledgers total: (production: " in cm

    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_open")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy_vdr.IndyVdrLedgerPool.context_close"
    )
    @async_mock.patch("indy_vdr.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy_vdr.IndyVdrLedger._submit")
    async def test_lookup_did_in_configured_ledgers_prod_not_cached(
        self, mock_submit, mock_build_get_nym_req, mock_close, mock_open
    ):
        with async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait:
            mock_build_get_nym_req.return_value = async_mock.MagicMock()
            mock_submit.return_value = json.dumps(GET_NYM_REPLY)
            mock_wait.return_value = mock_submit.return_value
            (
                ledger_id,
                ledger_inst,
            ) = await self.manager.lookup_did_in_configured_ledgers(
                "Av63wJYM7xYR4AiygYq4c3", cache_did=False
            )
            assert ledger_id == "test_prod_1"
            assert ledger_inst.pool.name == "test_prod_1"

    async def test_lookup_did_in_configured_ledgers_cached_prod_ledger(self):
        cache = InMemoryCache()
        await cache.set("did_ledger_id_resolver::Av63wJYM7xYR4AiygYq4c3", "test_prod_1")
        self.profile.context.injector.bind_instance(BaseCache, cache)
        (ledger_id, ledger_inst,) = await self.manager.lookup_did_in_configured_ledgers(
            "Av63wJYM7xYR4AiygYq4c3", cache_did=True
        )
        assert ledger_id == "test_prod_1"
        assert ledger_inst.pool.name == "test_prod_1"

    async def test_lookup_did_in_configured_ledgers_cached_non_prod_ledger(self):
        cache = InMemoryCache()
        await cache.set(
            "did_ledger_id_resolver::Av63wJYM7xYR4AiygYq4c3", "test_non_prod_2", None
        )
        self.profile.context.injector.bind_instance(BaseCache, cache)
        (ledger_id, ledger_inst,) = await self.manager.lookup_did_in_configured_ledgers(
            "Av63wJYM7xYR4AiygYq4c3", cache_did=True
        )
        assert ledger_id == "test_non_prod_2"
        assert ledger_inst.pool.name == "test_non_prod_2"

    async def test_lookup_did_in_configured_ledgers_cached_x(self):
        cache = InMemoryCache()
        await cache.set("did_ledger_id_resolver::Av63wJYM7xYR4AiygYq4c3", "invalid_id")
        self.profile.context.injector.bind_instance(BaseCache, cache)
        with self.assertRaises(MultipleLedgerManagerError) as cm:
            await self.manager.lookup_did_in_configured_ledgers(
                "Av63wJYM7xYR4AiygYq4c3", cache_did=True
            )
            assert "cached ledger_id invalid_id not found in either" in cm
