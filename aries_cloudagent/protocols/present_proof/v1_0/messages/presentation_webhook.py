"""v1.0 presentation exchange information webhook."""


class V10PresentationExchangeWebhook:
    """Class representing a state only presentation exchange webhook."""

    __acceptable_keys_list = [
        "connection_id",
        "presentation_exchange_id",
        "role",
        "initiator",
        "auto_present",
        "auto_verify",
        "error_msg",
        "state",
        "thread_id",
        "trace",
        "verified",
        "verified_msgs",
        "created_at",
        "updated_at",
    ]

    def __init__(
        self,
        **kwargs,
    ):
        """
        Initialize webhook object from V10PresentationExchange.

        from a list of accepted attributes.
        """
        [
            self.__setattr__(key, kwargs.get(key))
            for key in self.__acceptable_keys_list
            if kwargs.get(key) is not None
        ]
        if kwargs.get("_id") is not None:
            self.presentation_exchange_id = kwargs.get("_id")
