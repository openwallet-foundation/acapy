from django.db import models

from api_v2.models.Auditable import Auditable
from api_v2.models.User import User

from .CredentialHook import CredentialHook


# web hook subscriptions
class Subscription(Auditable):
    owner = models.ForeignKey(
        User, related_name="subscriptions", on_delete=models.CASCADE
    )

    # Subscription type = 'New', 'Stream', 'Topic'
    subscription_type = models.TextField(max_length=20)
    # Topic source id (required for 'Stream' and 'Topic' subscriptions)
    topic_source_id = models.TextField(blank=True, null=True)
    # Credential type (required for 'Stream' subscriptions)
    credential_type = models.ForeignKey(
        "api_v2.CredentialType",
        related_name="credential_subscription",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    # url to call (optional - can be provided per registration)
    target_url = models.TextField(max_length=240, blank=True, null=True)
    # token to provide with hook calls (optional - can be provided per registration)
    hook_token = models.TextField(max_length=240, blank=True, null=True)

    hook = models.ForeignKey(
        CredentialHook,
        related_name="credential_subscription",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    def __str__(self):
        return (
            str(id)
            + " "
            + self.owner.username
            + " "
            + self.subscription_type
            + " "
            + self.target_url
            + " "
            + str(self.hook.id)
        )

    def dict(self):
        return {
            "id": self.id,
            "owner": self.owner.username,
            "subscription_type": self.subscription_type,
            "topic_id": self.topic_source_id,
            "credential_type": self.credential_type,
            "target_url": self.target_url,
            "hook_token": self.hook_token,
        }
