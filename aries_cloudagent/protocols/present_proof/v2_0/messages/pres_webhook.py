"""v2.0 Presentation exchange record webhook."""


class V20PresExRecordWebhook:
    """Class representing a state only Presentation exchange record webhook."""

    __acceptable_keys_list = [
        "connection_id",
        "pres_ex_id",
        "role",
        "initiator",
        "auto_present",
        "auto_verify",
        "error_msg",
        "thread_id",
        "state",
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
        Initialize webhook object from V20PresExRecord.

        from a list of accepted attributes.
        """
        [
            self.__setattr__(key, kwargs.get(key))
            for key in self.__acceptable_keys_list
            if kwargs.get(key) is not None
        ]
        if kwargs.get("_id") is not None:
            self.pres_ex_id = kwargs.get("_id")
