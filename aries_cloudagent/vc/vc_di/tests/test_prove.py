"""test prove.py"""

import pytest
from aries_cloudagent.anoncreds.holder import AnonCredsHolderError
from aries_cloudagent.revocation.models.revocation_registry import RevocationRegistry
from aries_cloudagent.tests import mock
from aries_cloudagent.vc.ld_proofs.error import LinkedDataProofException

from ..prove import (
    _extract_cred_idx,
    _get_predicate_type_and_value,
    _load_w3c_credentials,
    create_rev_states,
)
from .test_manager import VC
from anoncreds import RevocationStatusList, CredentialRevocationState


def test__extract_cred_idx():
    item_path = "$.verifiableCredential[0]"
    assert _extract_cred_idx(item_path) == 0

    item_path = "$.verifiableCredential[42]"
    assert _extract_cred_idx(item_path) == 42


def test__get_predicate_type_and_value():
    pred_filter: dict[str, int] = {"exclusiveMinimum": 10}
    assert _get_predicate_type_and_value(pred_filter) == (">", 10)

    pred_filter = {"exclusiveMaximum": 20}
    assert _get_predicate_type_and_value(pred_filter) == ("<", 20)

    pred_filter = {"minimum": 5}
    assert _get_predicate_type_and_value(pred_filter) == (">=", 5)

    pred_filter = {"maximum": 15}
    assert _get_predicate_type_and_value(pred_filter) == ("<=", 15)


@pytest.mark.asyncio
async def test__load_w3c_credentials():
    credentials = [VC]

    w3c_creds = await _load_w3c_credentials(credentials)

    assert len(w3c_creds) == len(credentials)

    with pytest.raises(LinkedDataProofException) as context:
        credentials = [{"schema": "invalid"}]
        await _load_w3c_credentials(credentials)
    assert "Error loading credential as W3C credential"


@pytest.mark.asyncio
async def test_create_rev_states():
    w3c_creds_metadata = [
        {"rev_reg_id": "rev_reg_id_1", "rev_reg_index": 0, "timestamp": 1234567890},
        {"rev_reg_id": "rev_reg_id_2", "rev_reg_index": 1, "timestamp": 1234567890},
    ]
    rev_reg_defs = {
        "rev_reg_id_1": {"id": "rev_reg_id_1", "definition": "rev_reg_def_1"},
        "rev_reg_id_2": {"id": "rev_reg_id_2", "definition": "rev_reg_def_2"},
    }
    rev_reg_entries = {
        "rev_reg_id_1": {1234567890: "rev_reg_entry_1"},
        "rev_reg_id_2": {1234567890: "rev_reg_entry_2"},
    }

    with mock.patch.object(
        RevocationRegistry,
        "from_definition",
        return_value=mock.CoroutineMock(
            get_or_fetch_local_tails_path=mock.CoroutineMock(return_value="tails_path")
        ),
    ):
        with mock.patch.object(
            RevocationStatusList, "load", return_value=mock.MagicMock()
        ):
            with pytest.raises(AnonCredsHolderError):
                await create_rev_states(
                    w3c_creds_metadata, rev_reg_defs, rev_reg_entries
                )
            with mock.patch.object(
                CredentialRevocationState, "create", return_value=mock.MagicMock()
            ) as mock_create:

                result = await create_rev_states(
                    w3c_creds_metadata, rev_reg_defs, rev_reg_entries
                )

                assert len(result) == 2
                assert mock_create.call_count == 2
