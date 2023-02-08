class LightWeightWebhook:
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
    ]

    def __init__(
        self,
        version,  # 2 = V20CredExRecord ; 1 = V10CredentialExchange
        **kwargs,
    ):
        [
            self.__setattr__(key, kwargs.get(key))
            for key in self.__acceptable_keys_list
            if kwargs.get(key) is not None
        ]
        if version == 2:
            self.cred_ex_id = kwargs.get("_id")
        else:
            self.credential_exchange_id = kwargs.get("_id")
