from unittest import IsolatedAsyncioTestCase

import pytest

from aries_cloudagent.tests import mock

from ...askar.profile_anon import AskarAnoncredsProfile
from ...core.in_memory.profile import InMemoryProfile
from .. import revocation_setup as test_module
from ..events import (
    CredDefFinishedEvent,
    CredDefFinishedPayload,
    RevRegDefFinishedEvent,
    RevRegDefFinishedPayload,
)
from ..models.anoncreds_revocation import RevRegDef, RevRegDefValue
from ..revocation import AnonCredsRevocation


@pytest.mark.anoncreds
class TestAnonCredsRevocationSetup(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = InMemoryProfile.test_profile(
            settings={
                "wallet-type": "askar-anoncreds",
                "tails_server_base_url": "http://tails-server.com",
            },
            profile_class=AskarAnoncredsProfile,
        )
        self.revocation_setup = test_module.DefaultRevocationSetup()

    @mock.patch.object(
        AnonCredsRevocation,
        "create_and_register_revocation_registry_definition",
        return_value=None,
    )
    async def test_on_cred_def_support_revocation_registers_revocation_def(
        self, mock_register_revocation_registry_definition
    ):

        event = CredDefFinishedEvent(
            CredDefFinishedPayload(
                schema_id="schema_id",
                cred_def_id="cred_def_id",
                issuer_id="issuer_id",
                support_revocation=True,
                max_cred_num=100,
                options={},
            )
        )
        await self.revocation_setup.on_cred_def(self.profile, event)

        assert mock_register_revocation_registry_definition.called

    @mock.patch.object(
        AnonCredsRevocation,
        "create_and_register_revocation_registry_definition",
        return_value=None,
    )
    async def test_on_cred_def_author_with_auto_create_rev_reg_config_registers_reg_def(
        self, mock_register_revocation_registry_definition
    ):

        self.profile.settings["endorser.author"] = True
        self.profile.settings["endorser.auto_create_rev_reg"] = True
        event = CredDefFinishedEvent(
            CredDefFinishedPayload(
                schema_id="schema_id",
                cred_def_id="cred_def_id",
                issuer_id="issuer_id",
                support_revocation=False,
                max_cred_num=100,
                options={},
            )
        )
        await self.revocation_setup.on_cred_def(self.profile, event)

        assert mock_register_revocation_registry_definition.called

    @mock.patch.object(
        AnonCredsRevocation,
        "create_and_register_revocation_registry_definition",
        return_value=None,
    )
    async def test_on_cred_def_author_with_auto_create_rev_reg_config_and_support_revoc_option_registers_reg_def(
        self, mock_register_revocation_registry_definition
    ):

        self.profile.settings["endorser.author"] = True
        self.profile.settings["endorser.auto_create_rev_reg"] = True
        event = CredDefFinishedEvent(
            CredDefFinishedPayload(
                schema_id="schema_id",
                cred_def_id="cred_def_id",
                issuer_id="issuer_id",
                support_revocation=True,
                max_cred_num=100,
                options={},
            )
        )
        await self.revocation_setup.on_cred_def(self.profile, event)

        assert mock_register_revocation_registry_definition.called

    @mock.patch.object(
        AnonCredsRevocation,
        "create_and_register_revocation_registry_definition",
        return_value=None,
    )
    async def test_on_cred_def_not_author_or_support_rev_option(
        self, mock_register_revocation_registry_definition
    ):

        event = CredDefFinishedEvent(
            CredDefFinishedPayload(
                schema_id="schema_id",
                cred_def_id="cred_def_id",
                issuer_id="issuer_id",
                support_revocation=False,
                max_cred_num=100,
                options={},
            )
        )
        await self.revocation_setup.on_cred_def(self.profile, event)

        assert not mock_register_revocation_registry_definition.called

    @mock.patch.object(
        AnonCredsRevocation,
        "upload_tails_file",
        return_value=None,
    )
    @mock.patch.object(
        AnonCredsRevocation,
        "create_and_register_revocation_list",
        return_value=None,
    )
    @mock.patch.object(
        AnonCredsRevocation,
        "set_active_registry",
        return_value=None,
    )
    async def test_on_rev_reg_def_with_support_revoc_option_registers_list(
        self, mock_set_active_reg, mock_register, mock_upload
    ):
        event = RevRegDefFinishedEvent(
            RevRegDefFinishedPayload(
                rev_reg_def_id="rev_reg_def_id",
                rev_reg_def=RevRegDef(
                    tag="0",
                    cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                    value=RevRegDefValue(
                        max_cred_num=100,
                        public_keys={
                            "accum_key": {"z": "1 0BB...386"},
                        },
                        tails_hash="58NNWYnVxVFzAfUztwGSNBL4551XNq6nXk56pCiKJxxt",
                        tails_location="http://tails-server.com",
                    ),
                    issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                    type="CL_ACCUM",
                ),
                options={},
            )
        )

        await self.revocation_setup.on_rev_reg_def(self.profile, event)
        assert mock_upload.called
        assert mock_register.called
        assert mock_set_active_reg.called

    @mock.patch.object(
        AnonCredsRevocation,
        "upload_tails_file",
        return_value=None,
    )
    @mock.patch.object(
        AnonCredsRevocation,
        "create_and_register_revocation_list",
        return_value=None,
    )
    async def test_on_rev_reg_def_author_and_auto_create_rev_reg(
        self, mock_register, mock_upload
    ):
        self.profile.settings["endorser.author"] = True
        self.profile.settings["endorser.auto_create_rev_reg"] = True
        event = RevRegDefFinishedEvent(
            RevRegDefFinishedPayload(
                rev_reg_def_id="rev_reg_def_id",
                rev_reg_def=RevRegDef(
                    tag="tag",
                    cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                    value=RevRegDefValue(
                        max_cred_num=100,
                        public_keys={
                            "accum_key": {"z": "1 0BB...386"},
                        },
                        tails_hash="58NNWYnVxVFzAfUztwGSNBL4551XNq6nXk56pCiKJxxt",
                        tails_location="http://tails-server.com",
                    ),
                    issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                    type="CL_ACCUM",
                ),
                options={},
            )
        )

        await self.revocation_setup.on_rev_reg_def(self.profile, event)
        assert mock_upload.called
        assert mock_register.called

    @mock.patch.object(
        AnonCredsRevocation,
        "upload_tails_file",
        return_value=None,
    )
    @mock.patch.object(
        AnonCredsRevocation,
        "create_and_register_revocation_list",
        return_value=None,
    )
    async def test_on_rev_reg_def_author_and_do_not_auto_create_rev_reg(
        self, mock_register, mock_upload
    ):
        self.profile.settings["endorser.author"] = True
        self.profile.settings["endorser.auto_create_rev_reg"] = False
        event = RevRegDefFinishedEvent(
            RevRegDefFinishedPayload(
                rev_reg_def_id="rev_reg_def_id",
                rev_reg_def=RevRegDef(
                    tag="tag",
                    cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                    value=RevRegDefValue(
                        max_cred_num=100,
                        public_keys={
                            "accum_key": {"z": "1 0BB...386"},
                        },
                        tails_hash="58NNWYnVxVFzAfUztwGSNBL4551XNq6nXk56pCiKJxxt",
                        tails_location="http://tails-server.com",
                    ),
                    issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                    type="CL_ACCUM",
                ),
                options={},
            )
        )

        await self.revocation_setup.on_rev_reg_def(self.profile, event)
        assert not mock_upload.called
        assert not mock_register.called
