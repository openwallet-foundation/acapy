from django.db import models
from django.utils import timezone

from .Auditable import Auditable


class CredentialSet(Auditable):
    credential_type = models.ForeignKey(
        "CredentialType", related_name="credential_sets", on_delete=models.CASCADE
    )
    cardinality_hash = models.TextField(db_index=True, null=True)
    latest_credential = models.ForeignKey(
        "Credential", related_name="+", null=True, on_delete=models.SET_NULL
    )
    topic = models.ForeignKey(
        "Topic", related_name="credential_sets", on_delete=models.CASCADE
    )

    first_effective_date = models.DateTimeField(null=True)
    last_effective_date = models.DateTimeField(null=True)

    class Meta:
        db_table = "credential_set"
        unique_together = (("topic", "credential_type", "cardinality_hash"),)
        ordering = ("id",)
