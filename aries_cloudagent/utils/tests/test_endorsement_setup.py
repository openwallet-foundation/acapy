from unittest import IsolatedAsyncioTestCase

from aries_cloudagent.tests import mock

from ...connections.models.conn_record import ConnRecord
from ...core.in_memory.profile import InMemoryProfile
from .. import endorsement_setup
from ..endorsement_setup import attempt_auto_author_with_endorser_setup

mock_invitation = "http://localhost:9030?oob=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL291dC1vZi1iYW5kLzEuMS9pbnZpdGF0aW9uIiwgIkBpZCI6ICI2MWU1MmYzZS1kNTliLTQ3OWYtYmYwNC04NjJlOTk1MmM4MDYiLCAibGFiZWwiOiAiZW5kb3JzZXIiLCAiaGFuZHNoYWtlX3Byb3RvY29scyI6IFsiaHR0cHM6Ly9kaWRjb21tLm9yZy9kaWRleGNoYW5nZS8xLjAiXSwgInNlcnZpY2VzIjogW3siaWQiOiAiI2lubGluZSIsICJ0eXBlIjogImRpZC1jb21tdW5pY2F0aW9uIiwgInJlY2lwaWVudEtleXMiOiBbImRpZDprZXk6ejZNa2VkRDMyZlZmOG5ReG5SS2QzUmQ5S1hZQnVETEJiOHUyM1JWMm1ReFlpanR2I3o2TWtlZEQzMmZWZjhuUXhuUktkM1JkOUtYWUJ1RExCYjh1MjNSVjJtUXhZaWp0diJdLCAic2VydmljZUVuZHBvaW50IjogImh0dHA6Ly9sb2NhbGhvc3Q6OTAzMCJ9XX0="


class MockConnRecord:
    connection_id = "test-connection-id"


class TestEndorsementSetupUtil(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.profile = InMemoryProfile.test_profile()

    @mock.patch.object(endorsement_setup.LOGGER, "info", return_value=mock.MagicMock())
    async def test_not_enough_configs_for_connection(self, mock_logger):
        await endorsement_setup.attempt_auto_author_with_endorser_setup(self.profile)

        # No invitation
        self.profile.settings.set_value("endorser.author", True)
        await endorsement_setup.attempt_auto_author_with_endorser_setup(self.profile)

        # No endorser alias
        self.profile.settings.set_value("endorser.endorser_invitation", mock_invitation)
        await endorsement_setup.attempt_auto_author_with_endorser_setup(self.profile)

        # No endorser DID
        self.profile.settings.set_value("endorser.endorser_alias", "test-alias")
        await endorsement_setup.attempt_auto_author_with_endorser_setup(self.profile)

        assert mock_logger.call_count == 3
        for call in mock_logger.call_args_list:
            assert "Error accepting endorser invitation" not in call[0][0]

    @mock.patch.object(endorsement_setup.LOGGER, "info", return_value=mock.MagicMock())
    @mock.patch.object(endorsement_setup, "OutOfBandManager")
    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=ConnRecord(connection_id="test-connection-id"),
    )
    async def test_create_connection_with_valid_invitation(
        self, mock_conn_record, mock_oob_manager, mock_logger
    ):
        mock_oob_manager.return_value.receive_invitation = mock.CoroutineMock(
            return_value=MockConnRecord()
        )
        self.profile.settings.set_value("endorser.author", True)
        self.profile.settings.set_value("endorser.endorser_invitation", mock_invitation)
        self.profile.settings.set_value("endorser.endorser_alias", "test-alias")
        self.profile.settings.set_value("endorser.endorser_public_did", "test-did")

        await attempt_auto_author_with_endorser_setup(self.profile)

        for call in mock_logger.call_args_list:
            assert "Error accepting endorser invitation" not in call[0][0]

        assert mock_conn_record.called
