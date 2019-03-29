from django.db import models

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from .Auditable import Auditable

from .Address import Address
from .Attribute import Attribute
from .Name import Name


class Topic(Auditable):
    source_id = models.TextField()
    type = models.TextField()

    # Topics I have a verifiable relationship to
    related_to = models.ManyToManyField(
        "self",
        # Topics that have a verifiable relationship to me
        related_name="related_from",
        through="TopicRelationship",
        through_fields=("topic", "related_topic"),
        symmetrical=False,
    )

    _active_cred_ids = None

    class Meta:
        db_table = "topic"
        unique_together = (("source_id", "type"),)
        ordering = ('id',)

    def save(self, *args, **kwargs):
        """
        Call full_clean to apply form validation on save.
        We use this to prevent insertingtext fields with empty strings.
        """
        self.full_clean()
        super(Topic, self).save(*args, **kwargs)

    def get_active_credential_ids(self):
        if self._active_cred_ids is None:
            self._active_cred_ids = set(self.credentials.filter(latest=True, revoked=False)\
                .only('id', 'topic_id').values_list('id', flat=True))
        return self._active_cred_ids

    def get_active_addresses(self):
        creds = self.get_active_credential_ids()
        if creds:
            return Address.objects.filter(credential_id__in=creds)
        return []

    def get_active_attributes(self):
        creds = self.get_active_credential_ids()
        if creds:
            return Attribute.objects.filter(credential_id__in=creds)
        return []

    def get_active_names(self):
        creds = self.get_active_credential_ids()
        if creds:
            return Name.objects.filter(credential_id__in=creds)
        return []

    def get_active_related_to(self):
        return self.related_to.filter(
            from_rels__credential__latest=True,
            from_rels__credential__revoked=False)

    def get_active_related_from(self):
        return self.related_from.filter(
            to_rels__credential__latest=True,
            to_rels__credential__revoked=False)
