"""v2.0 credential exchange webhook."""


class V20CredExRecordWebhook:
    """Class representing a state only credential exchange webhook."""

    __acceptable_keys_list = [
        "connection_id",
        "credential_exchange_id",
        "cred_ex_id",
        "cred_def_id",
        "role",
        "initiator",
        "revoc_reg_id",
        "revocation_id",
        "auto_offer",
        "auto_issue",
        "auto_remove",
        "error_msg",
        "thread_id",
        "parent_thread_id",
        "state",
        "credential_definition_id",
        "schema_id",
        "credential_id",
        "trace",
        "public_did",
        "cred_id_stored",
        "conn_id",
        "created_at",
        "updated_at",
    ]

    def __init__(
        self,
        **kwargs,
    ):
        """
        Initialize webhook object from V20CredExRecord.

        from a list of accepted attributes.
        """
        [
            self.__setattr__(key, kwargs.get(key))
            for key in self.__acceptable_keys_list
            if kwargs.get(key) is not None
        ]
        if kwargs.get("_id") is not None:
            self.cred_ex_id = kwargs.get("_id")
