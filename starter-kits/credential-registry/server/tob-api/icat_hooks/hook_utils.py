from .models.CredentialHook import CredentialHook
from .models.Subscription import Subscription


def find_and_fire_hook(event_name, instance, **kwargs):
    filters = {"event": event_name, "is_active": True}

    hooks = CredentialHook.objects.filter(**filters)
    for hook in hooks:
        if hook.is_active:
            send_hook = False
            # TODO find subscription(s) related to this hook
            subscriptions = Subscription.objects.filter(hook=hook).all()
            if 0 < len(subscriptions):
                # TODO check if we should fire per subscription
                for subscription in subscriptions:
                    if subscription.subscription_type == "New":
                        if subscription.subscription_type == instance.topic_status:
                            send_hook = True
                    elif subscription.subscription_type == "Stream":
                        if (
                            subscription.topic_source_id == instance.corp_num
                            and subscription.credential_type == instance.credential_type
                        ):
                            send_hook = True
                    elif subscription.subscription_type == "Topic":
                        if subscription.topic_source_id == instance.corp_num:
                            send_hook = True
                    else:
                        print(
                            "      >>> Error invalid subscription type:",
                            subscription.subscription_type,
                        )

            # TODO logic around whether we hook or not
            if send_hook:
                hook.deliver_hook(instance)
