from django.db import models

from .Auditable import Auditable
from .User import User


# web hook subscriptions
class Subscription(Auditable):
    owner = models.ForeignKey(User, related_name="subscriptions", on_delete=models.CASCADE)

    # Subscription type = 'New', 'Stream', 'Topic'
    subscription_type = models.TextField(max_length=20)
    # Topic source id (required for 'Stream' and 'Topic' subscriptions)
    topic_source_id = models.TextField(blank=True, null=True)
    # Credential type (required for 'Stream' subscriptions)
    credential_type = models.ForeignKey("CredentialType", related_name="credentials", on_delete=models.CASCADE, blank=True, null=True)

    # url to call (optional - can be provided per registration)
    target_url = models.TextField(max_length=240, blank=True, null=True)
    # token to provide with hook calls (optional - can be provided per registration)
    hook_token = models.TextField(max_length=240, blank=True, null=True)
