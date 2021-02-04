"""Class for providing base utilities for Mediator support"""

from ..protocols.coordinate_mediation.v1_0.models.mediation_record import MediationRecord

from .base_manager import BaseConnectionManagerError


async def mediation_record_if_id(self, mediation_id: str = None):
        """Validate mediation and return record.

        If mediation_id is not None,
        validate mediation record state and return record
        else, return None
        """
        mediation_record = None
        if mediation_id:
            mediation_record = await MediationRecord.retrieve_by_id(
                self._session, mediation_id
            )
        if mediation_record:
            if mediation_record.state != MediationRecord.STATE_GRANTED:
                raise BaseConnectionManagerError(
                    "Mediation is not granted for mediation identified by "
                    f"{mediation_record.mediation_id}"
                )
        return mediation_record
