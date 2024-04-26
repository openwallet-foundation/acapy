"""Test the InvitationCreator class."""

from unittest.mock import MagicMock
import pytest

from ..manager import InvitationCreator, OutOfBandManagerError


@pytest.mark.parametrize(
    "args",
    [
        ({}),
        ({"metadata": "test"}),
        ({"attachments": "test", "multi_use": True}),
        ({"hs_protos": "test", "public": True, "use_did": True}),
        ({"hs_protos": "test", "public": True, "use_did_method": True}),
        ({"hs_protos": "test", "use_did": True, "use_did_method": True}),
        ({"hs_protos": "test", "create_unique_did": True}),
        ({"hs_protos": "test", "use_did_method": "some_did_method"}),
    ],
)
def test_init_param_checking_x(args):
    with pytest.raises(OutOfBandManagerError):
        InvitationCreator(
            profile=MagicMock(), route_manager=MagicMock(), oob=MagicMock(), **args
        )
