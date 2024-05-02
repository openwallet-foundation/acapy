import http
import json
import os
from unittest import IsolatedAsyncioTestCase

import pytest
from anoncreds import (
    Credential,
    CredentialDefinition,
    RevocationRegistryDefinition,
    RevocationRegistryDefinitionPrivate,
    RevocationStatusList,
    Schema,
)
from aries_askar import AskarError, AskarErrorCode
from requests import RequestException, Session

from aries_cloudagent.anoncreds.issuer import AnonCredsIssuer
from aries_cloudagent.anoncreds.models.anoncreds_cred_def import CredDef
from aries_cloudagent.anoncreds.models.anoncreds_revocation import (
    RevList,
    RevListResult,
    RevListState,
    RevRegDef,
    RevRegDefResult,
    RevRegDefState,
    RevRegDefValue,
)
from aries_cloudagent.anoncreds.models.anoncreds_schema import (
    AnonCredsSchema,
    GetSchemaResult,
)
from aries_cloudagent.anoncreds.registry import AnonCredsRegistry
from aries_cloudagent.anoncreds.tests.mock_objects import (
    MOCK_REV_REG_DEF,
)
from aries_cloudagent.anoncreds.tests.test_issuer import MockCredDefEntry
from aries_cloudagent.askar.profile_anon import (
    AskarAnoncredsProfile,
)
from aries_cloudagent.core.event_bus import Event, EventBus, MockEventBus
from aries_cloudagent.core.in_memory.profile import (
    InMemoryProfile,
    InMemoryProfileSession,
)
from aries_cloudagent.tests import mock

from .. import revocation as test_module

rev_reg_def = RevRegDef(
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
)

rev_list = RevList(
    issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
    current_accumulator="21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
    revocation_list=[0, 1, 1, 0],
    timestamp=1669640864487,
    rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
)


class MockRevRegDefEntry:
    def __init__(self, name="name"):
        self.name = name

    tags = {
        "state": RevRegDefState.STATE_ACTION,
    }
    value = "mock_value"
    value_json = {
        "value": {
            "maxCredNum": 100,
            "publicKeys": {"accumKey": {"z": "1 0BB...386"}},
            "tailsHash": "string",
            "tailsLocation": "string",
        },
        "credDefId": "CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
        "issuerId": "CsQY9MGeD3CQP4EyuVFo5m",
        "revocDefType": "CL_ACCUM",
        "tag": "string",
    }


class MockEntry:
    def __init__(
        self, name="name", value_json="", raw_value="raw-value", value="value", tags={}
    ) -> None:
        self.name = name
        self.value_json = value_json
        self.raw_value = raw_value
        self.value = value
        self.tags = tags


class MockRevListEntry:
    tags = {
        "state": RevListState.STATE_ACTION,
    }
    value = "mock_value"
    value_json = {
        "rev_list": {
            "issuerId": "CsQY9MGeD3CQP4EyuVFo5m",
            "revRegDefId": "4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
            "revocationList": [0, 1, 1, 0],
            "currentAccumulator": "21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
            "timestamp": 1669640864487,
        }
    }


@pytest.mark.anoncreds
class TestAnonCredsRevocation(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = InMemoryProfile.test_profile(
            settings={
                "wallet-type": "askar-anoncreds",
                "tails_server_base_url": "http://tails-server.com",
            },
            profile_class=AskarAnoncredsProfile,
        )
        self.revocation = test_module.AnonCredsRevocation(self.profile)

    async def test_init(self):
        assert self.revocation.profile == self.profile

    async def test_notify(self):
        self.profile.inject = mock.Mock(return_value=MockEventBus())
        await self.revocation.notify(Event(topic="test-topic"))

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_create_and_register_revocation_registry_definition_fails_to_get_cred_def(
        self, mock_handle
    ):
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                AskarError(code=AskarErrorCode.UNEXPECTED, message="test"),
                None,
            ]
        )

        # Anoncreds error
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.create_and_register_revocation_registry_definition(
                issuer_id="test-issuer-id",
                cred_def_id="test-cred-def-id",
                registry_type="test-registry-type",
                tag="test-tag",
                max_cred_num=100,
            )
        # fetch returns None
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.create_and_register_revocation_registry_definition(
                issuer_id="test-issuer-id",
                cred_def_id="test-cred-def-id",
                registry_type="test-registry-type",
                tag="test-tag",
                max_cred_num=100,
            )

    @mock.patch.object(InMemoryProfileSession, "handle")
    @mock.patch.object(
        test_module.AnonCredsRevocation,
        "generate_public_tails_uri",
        return_value="https://tails.uri",
    )
    @mock.patch.object(
        test_module.AnonCredsRevocation,
        "notify",
        return_value=None,
    )
    async def test_create_and_register_revocation_registry_definition(
        self, mock_notify, mock_tails_uri, mock_handle
    ):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                register_revocation_registry_definition=mock.CoroutineMock(
                    return_value=RevRegDefResult(
                        job_id="test-job-id",
                        revocation_registry_definition_state=RevRegDefState(
                            state=RevRegDefState.STATE_FINISHED,
                            revocation_registry_definition_id="active-reg-reg",
                            revocation_registry_definition=RevRegDef(
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
                        ),
                        registration_metadata={},
                        revocation_registry_definition_metadata={},
                    )
                )
            )
        )
        self.profile.transaction = mock.Mock(
            return_value=mock.MagicMock(
                insert=mock.CoroutineMock(return_value=None),
                commit=mock.CoroutineMock(return_value=None),
            )
        )
        schema = Schema.create(
            name="MYCO Biomarker",
            attr_names=["biomarker_id"],
            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
            version="1.0",
        )

        (cred_def, _, _) = CredentialDefinition.create(
            schema_id="CsQY9MGeD3CQP4EyuVFo5m:2:MYCO Biomarker:0.0.3",
            schema=schema,
            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
            tag="tag",
            support_revocation=True,
            signature_type="CL",
        )
        mock_handle.fetch = mock.CoroutineMock(
            return_value=MockEntry(raw_value=cred_def.to_json_buffer())
        )

        result = (
            await self.revocation.create_and_register_revocation_registry_definition(
                issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
                cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                registry_type="CL_ACCUM",
                tag="tag",
                max_cred_num=100,
            )
        )

        assert result is not None
        assert mock_handle.fetch.call_count == 1
        assert mock_tails_uri.call_count == 1
        assert mock_notify.call_count == 1

        # create doesn't fail with blank issuer id
        await self.revocation.create_and_register_revocation_registry_definition(
            issuer_id="",
            cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
            registry_type="CL_ACCUM",
            tag="tag",
            max_cred_num=100,
        )

        # register registry response missing rev_reg_def_id and job_id
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                register_revocation_registry_definition=mock.CoroutineMock(
                    side_effect=[
                        RevRegDefResult(
                            job_id=None,
                            revocation_registry_definition_state=RevRegDefState(
                                state=RevRegDefState.STATE_FINISHED,
                                revocation_registry_definition_id="active-reg-reg",
                                revocation_registry_definition=RevRegDef(
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
                            ),
                            registration_metadata={},
                            revocation_registry_definition_metadata={},
                        ),
                        RevRegDefResult(
                            job_id="test-job-id",
                            revocation_registry_definition_state=RevRegDefState(
                                state=RevRegDefState.STATE_FINISHED,
                                revocation_registry_definition_id=None,
                                revocation_registry_definition=RevRegDef(
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
                            ),
                            registration_metadata={},
                            revocation_registry_definition_metadata={},
                        ),
                        RevRegDefResult(
                            job_id=None,
                            revocation_registry_definition_state=RevRegDefState(
                                state=RevRegDefState.STATE_FINISHED,
                                revocation_registry_definition_id=None,
                                revocation_registry_definition=RevRegDef(
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
                            ),
                            registration_metadata={},
                            revocation_registry_definition_metadata={},
                        ),
                    ]
                )
            )
        )

        await self.revocation.create_and_register_revocation_registry_definition(
            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
            cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
            registry_type="CL_ACCUM",
            tag="tag",
            max_cred_num=100,
        )
        await self.revocation.create_and_register_revocation_registry_definition(
            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
            cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
            registry_type="CL_ACCUM",
            tag="tag",
            max_cred_num=100,
        )
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.create_and_register_revocation_registry_definition(
                issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
                cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                registry_type="CL_ACCUM",
                tag="tag",
                max_cred_num=100,
            )

    @mock.patch.object(InMemoryProfileSession, "handle")
    @mock.patch.object(RevRegDef, "from_json", return_value="rev-reg-def")
    @mock.patch.object(test_module.AnonCredsRevocation, "notify")
    async def test_finish_revocation_registry_definition(
        self, mock_notify, mock_from_json, mock_handle
    ):
        mock_handle.fetch = mock.CoroutineMock(return_value=MockEntry())
        mock_handle.insert = mock.CoroutineMock(return_value=None)
        mock_handle.remove = mock.CoroutineMock(return_value=None)

        await self.revocation.finish_revocation_registry_definition(
            job_id="job-id",
            rev_reg_def_id="rev-reg-def-id",
        )

        # None response
        mock_handle.fetch = mock.CoroutineMock(return_value=None)
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.finish_revocation_registry_definition(
                job_id="job-id",
                rev_reg_def_id="rev-reg-def-id",
            )

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_get_created_revocation_registry_definitions(self, mock_handle):
        mock_handle.fetch_all = mock.CoroutineMock(
            return_value=[
                MockEntry("revocation_reg_def_0"),
                MockEntry("revocation_reg_def_1"),
            ]
        )
        result = await self.revocation.get_created_revocation_registry_definitions()
        assert result == ["revocation_reg_def_0", "revocation_reg_def_1"]

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_get_created_revocation_registry_definition_state(self, mock_handle):
        mock_handle.fetch = mock.CoroutineMock(side_effect=[MockEntry(), None])
        result = await self.revocation.get_created_revocation_registry_definition_state(
            "test-rev-reg-def-id"
        )
        assert result == RevRegDefState.STATE_FINISHED
        result = await self.revocation.get_created_revocation_registry_definition_state(
            "test-rev-reg-def-id"
        )
        assert result is None

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_get_created_revocation_registry_definition(self, mock_handle):
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                MockEntry(
                    value_json=RevRegDef(
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
                    ).to_json()
                ),
                None,
            ]
        )
        result = await self.revocation.get_created_revocation_registry_definition(
            "test-rev-reg-def-id"
        )
        assert isinstance(result, RevRegDef)
        result = await self.revocation.get_created_revocation_registry_definition(
            "test-rev-reg-def-id"
        )
        assert result is None

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_set_active_registry(self, mock_handle):
        mock_handle.fetch = mock.CoroutineMock(return_value=None)
        mock_handle.replace = mock.CoroutineMock(return_value=None)
        inactive_tags = {
            "active": "false",
            "cred_def_id": "test-cred-def-id",
        }

        # fetch returns None
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.set_active_registry(
                rev_reg_def_id="test-rev-reg-def-id",
            )
        # Already active
        mock_handle.fetch = mock.CoroutineMock(
            return_value=MockEntry(
                tags={
                    "active": "true",
                    "cred_def_id": "test-cred-def-id",
                }
            )
        )
        await self.revocation.set_active_registry(
            rev_reg_def_id="test-rev-reg-def-id",
        )

        mock_handle.fetch = mock.CoroutineMock(
            return_value=MockEntry(tags=inactive_tags)
        )
        mock_handle.fetch_all = mock.CoroutineMock(
            return_value=[MockEntry(tags=inactive_tags), MockEntry(tags=inactive_tags)]
        )
        await self.revocation.set_active_registry(
            rev_reg_def_id="test-rev-reg-def-id",
        )

        assert mock_handle.fetch.call_count == 1
        assert mock_handle.fetch_all.call_count == 1
        assert mock_handle.replace.call_count == 3

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_create_and_register_revocation_list_errors(self, mock_handle):
        class MockEntry:
            value_json = {
                "credDefId": "CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
            }

        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                # failed to get cred def
                AskarError(code=AskarErrorCode.UNEXPECTED, message="test"),
                MockEntry(),
                # failed to get rev reg def
                MockEntry(),
                AskarError(code=AskarErrorCode.UNEXPECTED, message="test"),
                # failed to get cred def
                MockEntry(),
                MockEntry(),
                AskarError(code=AskarErrorCode.UNEXPECTED, message="test"),
            ]
        )
        # askar error
        for _ in range(3):
            with self.assertRaises(test_module.AnonCredsRevocationError):
                await self.revocation.create_and_register_revocation_list(
                    rev_reg_def_id="test-rev-reg-def-id",
                )

    @mock.patch.object(InMemoryProfileSession, "handle")
    @mock.patch.object(RevRegDef, "deserialize")
    @mock.patch.object(CredDef, "deserialize")
    @mock.patch.object(RevocationRegistryDefinitionPrivate, "load")
    @mock.patch.object(RevocationStatusList, "create")
    async def test_create_and_register_revocation_list(
        self,
        mock_list_create,
        mock_load_rev_list,
        mock_deserialize_cred_def,
        mock_deserialize_rev_reg,
        mock_handle,
    ):
        mock_list_create.return_value = RevocationStatusList.load(
            {
                "issuerId": "CsQY9MGeD3CQP4EyuVFo5m",
                "revRegDefId": "4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
                "revocationList": [0, 1, 1, 0],
                "currentAccumulator": "21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                "timestamp": 1669640864487,
            }
        )
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                MockEntry(
                    value_json={
                        "credDefId": "CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                        "issuerId": "CsQY9MGeD3CQP4EyuVFo5m",
                        "revocDefType": "CL_ACCUM",
                        "tag": "string",
                        "value": {
                            "maxCredNum": 0,
                            "publicKeys": {
                                "accumKey": {"z": "1 0BB...386"},
                            },
                            "tailsHash": "string",
                            "tailsLocation": "string",
                        },
                    }
                ),
                MockRevListEntry(),
                MockCredDefEntry(),
            ]
        )
        mock_handle.insert = mock.CoroutineMock(return_value=None)

        self.profile.context.injector.bind_instance(
            AnonCredsRegistry,
            mock.MagicMock(
                register_revocation_list=mock.CoroutineMock(
                    return_value=RevListResult(
                        job_id="test-job-id",
                        revocation_list_state=RevListState(
                            revocation_list=rev_list,
                            state=RevListState.STATE_FINISHED,
                        ),
                        registration_metadata={},
                        revocation_list_metadata={},
                    )
                )
            ),
        )
        self.profile.context.injector.bind_instance(EventBus, MockEventBus())
        await self.revocation.create_and_register_revocation_list(
            rev_reg_def_id="test-rev-reg-def-id",
        )

        assert mock_handle.fetch.called
        assert mock_handle.insert.called
        assert mock_list_create.called
        assert mock_deserialize_cred_def.called
        assert mock_deserialize_rev_reg.called
        assert mock_load_rev_list.called
        assert self.profile.context.injector.get_provider(
            AnonCredsRegistry
        )._instance.register_revocation_list.called

    @mock.patch.object(InMemoryProfileSession, "handle")
    @mock.patch.object(test_module.AnonCredsRevocation, "_finish_registration")
    async def test_finish_revocation_list(self, mock_finish, mock_handle):
        self.profile.context.injector.bind_instance(EventBus, MockEventBus())

        mock_handle.fetch = mock.CoroutineMock(side_effect=[None, MockEntry()])

        # Fetch doesn't find list then it should be created
        await self.revocation.finish_revocation_list(
            job_id="test-job-id", rev_reg_def_id="test-rev-reg-def-id", revoked=[]
        )
        assert mock_finish.called

        # Fetch finds list then there's nothing to do, it's already finished and updated
        await self.revocation.finish_revocation_list(
            job_id="test-job-id", rev_reg_def_id="test-rev-reg-def-id", revoked=[]
        )
        assert mock_finish.call_count == 1

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_update_revocation_list_get_rev_reg_errors(self, mock_handle):
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                AskarError(code=AskarErrorCode.UNEXPECTED, message="test"),
                None,
            ]
        )
        # askar error
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.update_revocation_list(
                rev_reg_def_id="test-rev-reg-def-id",
                prev=rev_list,
                curr=rev_list,
                revoked=[1, 1, 0, 0],
            )
        # fetch returns None
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.update_revocation_list(
                rev_reg_def_id="test-rev-reg-def-id",
                prev=rev_list,
                curr=rev_list,
                revoked=[1, 1, 0, 0],
            )

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_update_revocation_list(self, mock_handle):
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                MockRevRegDefEntry(),
                MockRevListEntry(),
                MockRevListEntry(),
            ]
        )
        mock_handle.replace = mock.CoroutineMock(return_value=None)

        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                update_revocation_list=mock.CoroutineMock(
                    return_value=RevListResult(
                        job_id="test-job-id",
                        revocation_list_state=RevListState(
                            revocation_list=rev_list,
                            state=RevListState.STATE_FINISHED,
                        ),
                        registration_metadata={},
                        revocation_list_metadata={},
                    )
                )
            )
        )

        # valid with no errors
        result = await self.revocation.update_revocation_list(
            rev_reg_def_id="test-rev-reg-def-id",
            prev=rev_list,
            curr=rev_list,
            revoked=[1, 1, 0, 0],
        )

        assert mock_handle.fetch.call_count == 3
        assert mock_handle.replace.called
        assert result is not None

        # askar error fetching list is caught
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                MockRevRegDefEntry(),
                AskarError(code=AskarErrorCode.UNEXPECTED, message="test"),
            ]
        )
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.update_revocation_list(
                rev_reg_def_id="test-rev-reg-def-id",
                prev=rev_list,
                curr=rev_list,
                revoked=[1, 1, 0, 0],
            )

        # fail to get list
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                MockRevRegDefEntry(),
                None,
            ]
        )
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.update_revocation_list(
                rev_reg_def_id="test-rev-reg-def-id",
                prev=rev_list,
                curr=rev_list,
                revoked=[1, 1, 0, 0],
            )

        # revocation lists don't match
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                MockRevRegDefEntry(),
                MockRevListEntry(),
            ]
        )
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.update_revocation_list(
                rev_reg_def_id="test-rev-reg-def-id",
                prev=rev_list,
                curr=RevList(
                    issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                    current_accumulator="21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                    revocation_list=[1, 0, 1, 0],
                    timestamp=1669640864487,
                    rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
                ),
                revoked=[1, 1, 0, 0],
            )

        # update fail states are caught
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                MockRevRegDefEntry(),
                MockRevListEntry(),
                AskarError(code=AskarErrorCode.UNEXPECTED, message="test"),
            ]
        )
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.update_revocation_list(
                rev_reg_def_id="test-rev-reg-def-id",
                prev=rev_list,
                curr=rev_list,
                revoked=[1, 1, 0, 0],
            )
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                MockRevRegDefEntry(),
                MockRevListEntry(),
                None,
            ]
        )
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.update_revocation_list(
                rev_reg_def_id="test-rev-reg-def-id",
                prev=rev_list,
                curr=rev_list,
                revoked=[1, 1, 0, 0],
            )

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_get_created_revocation_list(self, mock_handle):
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                MockRevListEntry(),
                None,
                AskarError(code=AskarErrorCode.UNEXPECTED, message="test"),
            ]
        )
        result = await self.revocation.get_created_revocation_list("rev-reg-def-id")
        assert mock_handle.fetch.call_count == 1
        assert result is not None

        # fetch returns None
        result = await self.revocation.get_created_revocation_list("rev-reg-def-id")
        assert result is None

        # askar error
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.get_created_revocation_list("rev-reg-def-id")

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_get_revocation_lists_with_pending_revocations(self, mock_handle):
        mock_handle.fetch_all = mock.CoroutineMock(
            side_effect=[
                [MockEntry("rev_list_0"), MockEntry("rev_list_1")],
                [],
                AskarError(code=AskarErrorCode.UNEXPECTED, message="test"),
            ]
        )
        result = await self.revocation.get_revocation_lists_with_pending_revocations()
        assert result == ["rev_list_0", "rev_list_1"]

        # fetch returns None
        result = await self.revocation.get_revocation_lists_with_pending_revocations()
        assert result == []

        # askar error
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.get_revocation_lists_with_pending_revocations()

    @mock.patch.object(Session, "get")
    @mock.patch.object(os, "remove")
    async def test_retrieve_tails(self, mock_remove, mock_get):
        class MockResponse:
            def __init__(self, status=http.HTTPStatus.OK):
                self.status_code = status

            def iter_content(self, chunk_size: int = 1):
                yield b"tails-hash"

        mock_get.side_effect = [
            MockResponse(),
            MockResponse(),
            RequestException(request=mock.AsyncMock(), response=mock.AsyncMock()),
            MockResponse(status=http.HTTPStatus.BAD_REQUEST),
        ]

        result = await self.revocation.retrieve_tails(rev_reg_def)

        assert isinstance(result, str)
        assert mock_get.call_count == 1

        # tails hash does not match
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.retrieve_tails(
                RevRegDef(
                    tag="tag",
                    cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                    value=RevRegDefValue(
                        max_cred_num=100,
                        public_keys={
                            "accum_key": {"z": "1 0BB...386"},
                        },
                        tails_hash="not-correct-hash",
                        tails_location="http://tails-server.com",
                    ),
                    issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                    type="CL_ACCUM",
                )
            )
            assert mock_remove.call_count == 1

        # http request fails
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.retrieve_tails(rev_reg_def)

        # doesn't crash on non 200 response
        await self.revocation.retrieve_tails(rev_reg_def)

    def test_generate_public_tails_uri(self):
        self.revocation.generate_public_tails_uri(rev_reg_def)

        # invalid url
        self.profile.settings["tails_server_base_url"] = "invalid-url"
        with self.assertRaises(test_module.AnonCredsRevocationError):
            self.revocation.generate_public_tails_uri(rev_reg_def)

        # tails server base url setting is missing
        del self.profile.settings["tails_server_base_url"]
        with self.assertRaises(test_module.AnonCredsRevocationError):
            self.revocation.generate_public_tails_uri(rev_reg_def)

    async def test_upload_tails_file(self):
        self.profile.inject_or = mock.Mock(
            return_value=mock.MagicMock(
                upload_tails_file=mock.CoroutineMock(
                    side_effect=[
                        (True, "http://tails-server.com"),
                        (None, "http://tails-server.com"),
                        (True, "not-http://tails-server.com"),
                    ]
                )
            )
        )
        # valid
        await self.revocation.upload_tails_file(rev_reg_def)
        # upload fails
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.upload_tails_file(rev_reg_def)
        # tails location does not match
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.upload_tails_file(rev_reg_def)

        # tails server base url setting is missing
        self.profile.inject_or = mock.Mock(return_value=None)
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.upload_tails_file(rev_reg_def)

    @mock.patch.object(InMemoryProfileSession, "handle")
    @mock.patch.object(
        test_module.AnonCredsRevocation, "set_active_registry", return_value=None
    )
    @mock.patch.object(
        test_module.AnonCredsRevocation,
        "create_and_register_revocation_registry_definition",
        return_value="backup",
    )
    async def test_handle_full_registry(
        self, mock_create_and_register, mock_set_active_registry, mock_handle
    ):
        mock_handle.fetch = mock.CoroutineMock(return_value=MockRevRegDefEntry())
        mock_handle.fetch_all = mock.CoroutineMock(
            return_value=[
                MockRevRegDefEntry(),
                MockRevRegDefEntry(),
            ]
        )
        mock_handle.replace = mock.CoroutineMock(return_value=None)

        await self.revocation.handle_full_registry("test-rev-reg-def-id")
        assert mock_create_and_register.called
        assert mock_set_active_registry.called
        assert mock_handle.fetch.call_count == 2
        assert mock_handle.fetch_all.called
        assert mock_handle.replace.called

        # no backup registry available
        mock_handle.fetch_all = mock.CoroutineMock(return_value=[])
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.handle_full_registry("test-rev-reg-def-id")

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_decommission_registry(self, mock_handle):
        mock_handle.fetch_all = mock.CoroutineMock(
            return_value=[
                MockEntry(
                    name="active-reg-reg",
                    tags={
                        "state": RevRegDefState.STATE_FINISHED,
                        "active": True,
                    },
                ),
                MockEntry(
                    name="new-rev-reg",
                    tags={
                        "state": RevRegDefState.STATE_FINISHED,
                        "active": True,
                    },
                ),
            ]
        )
        # active registry
        self.revocation.get_or_create_active_registry = mock.CoroutineMock(
            return_value=RevRegDefResult(
                job_id="test-job-id",
                revocation_registry_definition_state=RevRegDefState(
                    state=RevRegDefState.STATE_FINISHED,
                    revocation_registry_definition_id="active-reg-reg",
                    revocation_registry_definition=rev_reg_def,
                ),
                registration_metadata={},
                revocation_registry_definition_metadata={},
            )
        )
        # new active
        self.revocation.create_and_register_revocation_registry_definition = (
            mock.CoroutineMock(
                return_value=RevRegDefResult(
                    job_id="test-job-id",
                    revocation_registry_definition_state=RevRegDefState(
                        state=RevRegDefState.STATE_ACTION,
                        revocation_registry_definition_id="new-rev-reg",
                        revocation_registry_definition=rev_reg_def,
                    ),
                    registration_metadata={},
                    revocation_registry_definition_metadata={},
                )
            )
        )
        self.revocation.set_active_registry = mock.CoroutineMock(return_value=None)
        mock_handle.replace = mock.CoroutineMock(return_value=None)

        result = await self.revocation.decommission_registry("test-rev-reg-def-id")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].tags["active"] == "false"
        assert result[0].tags["state"] == RevRegDefState.STATE_DECOMMISSIONED
        assert mock_handle.fetch_all.called
        assert mock_handle.replace.called
        # # One for backup
        assert (
            self.revocation.create_and_register_revocation_registry_definition.call_count
            == 2
        )

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_get_or_create_active_registry(self, mock_handle):
        mock_handle.fetch_all = mock.CoroutineMock(
            side_effect=[
                [MockRevRegDefEntry("reg-1"), MockRevRegDefEntry("reg-0")],
                None,
            ]
        )

        # valid
        result = await self.revocation.get_or_create_active_registry(
            "test-rev-reg-def-id"
        )
        assert isinstance(result, RevRegDefResult)
        assert result.revocation_registry_definition_state.state == (
            RevRegDefState.STATE_FINISHED
        )
        assert (
            result.revocation_registry_definition_state.revocation_registry_definition_id
            == ("reg-1")
        )

        # no active registry, todo: create one
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.get_or_create_active_registry("test-rev-reg-def-id")

    @mock.patch.object(InMemoryProfileSession, "handle")
    @mock.patch.object(Credential, "create", return_value=mock.MagicMock())
    async def test_create_credential_private_no_rev_reg_or_tails(
        self, mock_create, mock_handle
    ):
        mock_handle.fetch = mock.CoroutineMock(side_effect=[MockEntry(), MockEntry()])
        await self.revocation._create_credential(
            credential_definition_id="test-cred-def-id",
            schema_attributes=["attr1", "attr2"],
            credential_offer={
                "schema_id": "CsQY9MGeD3CQP4EyuVFo5m:2:MYCO Biomarker:0.0.3",
                "cred_def_id": "CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                "key_correctness_proof": {},
                "nonce": "nonce",
            },
            credential_request={},
            credential_values={
                "attr1": "value1",
                "attr2": "value2",
            },
        )
        assert mock_create.called

        # askar error retrieving cred def
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=AskarError(AskarErrorCode.UNEXPECTED, "test")
        )
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation._create_credential(
                credential_definition_id="test-cred-def-id",
                schema_attributes=["attr1", "attr2"],
                credential_offer={},
                credential_request={},
                credential_values={},
            )

        # missing cred def or cred def private
        mock_handle.fetch = mock.CoroutineMock(side_effect=[None, MockEntry()])
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation._create_credential(
                credential_definition_id="test-cred-def-id",
                schema_attributes=["attr1", "attr2"],
                credential_offer={},
                credential_request={},
                credential_values={},
            )
        mock_handle.fetch = mock.CoroutineMock(side_effect=[MockEntry(), None])
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation._create_credential(
                credential_definition_id="test-cred-def-id",
                schema_attributes=["attr1", "attr2"],
                credential_offer={},
                credential_request={},
                credential_values={},
            )

    @mock.patch.object(InMemoryProfileSession, "handle")
    @mock.patch.object(
        RevocationRegistryDefinition, "load", return_value=rev_reg_def.value
    )
    @mock.patch("aries_cloudagent.anoncreds.revocation.CredentialRevocationConfig")
    @mock.patch.object(Credential, "create", return_value=mock.MagicMock())
    async def test_create_credential_private_with_rev_reg_and_tails(
        self, mock_create, mock_config, mock_load_rev_reg_def, mock_handle
    ):
        async def call_test_func():
            await self.revocation._create_credential(
                credential_definition_id="test-cred-def-id",
                schema_attributes=["attr1", "attr2"],
                credential_offer={
                    "schema_id": "CsQY9MGeD3CQP4EyuVFo5m:2:MYCO Biomarker:0.0.3",
                    "cred_def_id": "CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                    "key_correctness_proof": {},
                    "nonce": "nonce",
                },
                credential_request={},
                credential_values={
                    "attr1": "value1",
                    "attr2": "value2",
                },
                rev_reg_def_id="test-rev-reg-def-id",
                tails_file_path="tails-file-path",
            )

        # missing rev list
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[MockEntry(), MockEntry(), None, MockEntry(), MockEntry()]
        )
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await call_test_func()
        # missing rev def
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[MockEntry(), MockEntry(), MockEntry(), None, MockEntry()]
        )
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await call_test_func()
        # missing rev key
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[MockEntry(), MockEntry(), MockEntry(), MockEntry(), None]
        )
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await call_test_func()

        # valid
        mock_handle.replace = mock.CoroutineMock(return_value=None)
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                MockEntry(),
                MockEntry(),
                MockEntry(
                    value_json={
                        "rev_list": rev_list.serialize(),
                        "next_index": 0,
                    }
                ),
                MockEntry(raw_value=rev_reg_def.serialize()),
                MockEntry(),
            ]
        )
        await call_test_func()
        assert mock_create.called
        assert mock_handle.replace.called
        assert mock_handle.fetch.call_count == 5

        # revocation registry is full
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                MockEntry(),
                MockEntry(),
                MockEntry(
                    value_json={
                        "rev_list": rev_list.serialize(),
                        "next_index": 101,
                    }
                ),
                MockEntry(raw_value=rev_reg_def.serialize()),
                MockEntry(),
            ]
        )
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await call_test_func()

    @mock.patch.object(
        AnonCredsIssuer, "cred_def_supports_revocation", return_value=True
    )
    async def test_create_credential(self, mock_supports_revocation):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_schema=mock.CoroutineMock(
                    return_value=GetSchemaResult(
                        schema_id="CsQY9MGeD3CQP4EyuVFo5m:2:MYCO Biomarker:0.0.3",
                        schema=AnonCredsSchema(
                            issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                            name="MYCO Biomarker:0.0.3",
                            version="1.0",
                            attr_names=["attr1", "attr2"],
                        ),
                        schema_metadata={},
                        resolution_metadata={},
                    )
                )
            )
        )
        self.revocation.get_or_create_active_registry = mock.CoroutineMock(
            return_value=RevRegDefResult(
                job_id="test-job-id",
                revocation_registry_definition_state=RevRegDefState(
                    state=RevRegDefState.STATE_FINISHED,
                    revocation_registry_definition_id="active-reg-reg",
                    revocation_registry_definition=rev_reg_def,
                ),
                registration_metadata={},
                revocation_registry_definition_metadata={},
            )
        )

        # Test private funtion seperately - very large
        self.revocation._create_credential = mock.CoroutineMock(
            return_value=({"cred": "cred"}, 98)
        )

        result = await self.revocation.create_credential(
            credential_offer={
                "schema_id": "CsQY9MGeD3CQP4EyuVFo5m:2:MYCO Biomarker:0.0.3",
                "cred_def_id": "CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                "key_correctness_proof": {},
                "nonce": "nonce",
            },
            credential_request={},
            credential_values={},
        )

        assert isinstance(result, tuple)
        assert mock_supports_revocation.call_count == 1

    @mock.patch.object(InMemoryProfileSession, "handle")
    @mock.patch.object(RevList, "to_native")
    @mock.patch.object(RevList, "from_native", return_value=None)
    @mock.patch.object(RevRegDef, "to_native")
    @mock.patch.object(CredDef, "deserialize")
    @mock.patch.object(RevocationRegistryDefinitionPrivate, "load")
    async def test_revoke_pending_credentials(
        self,
        mock_load_rev_reg,
        mock_deserialize_cred_def,
        mock_rev_reg_to_native,
        mock_rev_list_from_native,
        mock_rev_list_to_native,
        mock_handle,
    ):
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                # askar error
                AskarError(code=AskarErrorCode.UNEXPECTED, message="test"),
                # missing rev reg def
                None,
                MockEntry(value_json=json.dumps({})),
                MockEntry(value_json=json.dumps({})),
                # missing rev list
                MockEntry(value_json=json.dumps({})),
                None,
                MockEntry(value_json=json.dumps({})),
                # missing rev private
                MockEntry(value_json=json.dumps({})),
                MockEntry(value_json=json.dumps({})),
                None,
            ]
        )

        # askar error
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.revoke_pending_credentials(
                revoc_reg_id="test-rev-reg-id",
            )
        # rev reg def not found
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.revoke_pending_credentials(
                revoc_reg_id="test-rev-reg-id",
            )
        # rev red def private not found
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.revoke_pending_credentials(
                revoc_reg_id="test-rev-reg-id",
            )
        # rev list not found
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.revoke_pending_credentials(
                revoc_reg_id="test-rev-reg-id",
            )

        # valid
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                # rev_reg_def_entry
                MockEntry(value_json=MOCK_REV_REG_DEF),
                # rev_list_entry
                MockEntry(
                    value_json={
                        "pending": [0, 1, 4, 3],
                        "next_index": 4,
                        "rev_list": rev_list.serialize(),
                    }
                ),
                # private rev reg def
                MockEntry(),
                # cred def
                MockEntry(),
                # updated rev list entry
                MockEntry(
                    value_json={
                        "pending": [0, 1, 4, 3],
                        "next_index": 4,
                        "rev_list": rev_list.serialize(),
                    },
                    tags={"pending": []},
                ),
            ]
        )
        mock_handle.replace = mock.CoroutineMock(return_value=None)

        result = await self.revocation.revoke_pending_credentials(
            revoc_reg_id="test-rev-reg-id",
        )

        assert mock_handle.fetch.call_count == 5
        assert mock_handle.replace.called
        assert mock_rev_list_from_native.called
        assert mock_rev_list_to_native.called
        assert mock_rev_reg_to_native.called
        assert mock_load_rev_reg.called
        assert mock_deserialize_cred_def.called
        assert isinstance(result, test_module.RevokeResult)

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_mark_pending_revocations(self, mock_handle):
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                None,
                MockEntry(
                    value_json={
                        "pending": [1],
                    }
                ),
            ]
        )
        mock_handle.replace = mock.CoroutineMock(return_value=None)

        # rev list entry not found
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.mark_pending_revocations(
                "test-rev-reg-id", int("200")
            )

        # valid
        await self.revocation.mark_pending_revocations("test-rev-reg-id", int("200"))
        assert mock_handle.replace.call_count == 1

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_get_pending_revocations(self, mock_handle):
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                None,
                MockEntry(
                    value_json={
                        "pending": [1, 2],
                    }
                ),
            ]
        )

        result = await self.revocation.get_pending_revocations("test-rev-reg-id")
        assert result == []

        result = await self.revocation.get_pending_revocations("test-rev-reg-id")
        assert result == [1, 2]

    @mock.patch.object(InMemoryProfileSession, "handle")
    @mock.patch("aries_cloudagent.anoncreds.revocation.isinstance")
    async def test_clear_pending_revocations(self, mock_is_instance, mock_handle):
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                None,
                MockEntry(
                    value_json={
                        "pending": [1, 2],
                    }
                ),
                MockEntry(
                    value_json={
                        "pending": [1, 2],
                    }
                ),
            ]
        )
        mock_handle.replace = mock.CoroutineMock(return_value=None)

        # fetch is None
        with self.assertRaises(test_module.AnonCredsRevocationError):
            await self.revocation.clear_pending_revocations(
                self.profile.session(), rev_reg_def_id="test-rev-reg-id"
            )
        # valid
        await self.revocation.clear_pending_revocations(
            self.profile.session(), rev_reg_def_id="test-rev-reg-id"
        )
        assert mock_handle.replace.called
        # with crid mask
        await self.revocation.clear_pending_revocations(
            self.profile.session(), rev_reg_def_id="test-rev-reg-id", crid_mask=[1, 2]
        )

    async def test_clear_pending_revocations_with_non_anoncreds_session(self):
        with self.assertRaises(ValueError):
            await self.revocation.clear_pending_revocations(
                self.profile.session(), rev_reg_def_id="test-rev-reg-id"
            )
