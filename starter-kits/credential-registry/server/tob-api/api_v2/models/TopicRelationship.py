from django.db import models
from django.utils import timezone

from .Auditable import Auditable

from .Topic import Topic


class TopicRelationship(Auditable):
    credential = models.ForeignKey("Credential", related_name="topic_rels", on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, related_name="from_rels", on_delete=models.CASCADE)
    related_topic = models.ForeignKey(Topic, related_name="to_rels", on_delete=models.CASCADE)

    class Meta:
        db_table = "topic_relationship"
        ordering = ('id',)

    @property
    def credential_attributes(self):
        return self.credential.attributes.all()
