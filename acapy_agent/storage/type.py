"""Library version information."""

RECORD_TYPE_ACAPY_STORAGE_TYPE = "acapy_storage_type"
RECORD_TYPE_ACAPY_UPGRADING = "acapy_upgrading"

STORAGE_TYPE_VALUE_ANONCREDS = "askar-anoncreds"
STORAGE_TYPE_VALUE_ASKAR = "askar"

# Event persistence record types for revocation registry management
RECORD_TYPE_REV_REG_DEF_CREATE_EVENT = "rev_reg_def_create_event"
RECORD_TYPE_REV_REG_DEF_STORE_EVENT = "rev_reg_def_store_event"
RECORD_TYPE_TAILS_UPLOAD_EVENT = "tails_upload_event"
RECORD_TYPE_REV_LIST_CREATE_EVENT = "rev_list_create_event"
RECORD_TYPE_REV_LIST_STORE_EVENT = "rev_list_store_event"
RECORD_TYPE_REV_REG_ACTIVATION_EVENT = "rev_reg_activation_event"
RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT = "rev_reg_full_handling_event"

# Event states
EVENT_STATE_REQUESTED = "requested"
EVENT_STATE_RESPONSE_SUCCESS = "response_success"
EVENT_STATE_RESPONSE_FAILURE = "response_failure"
EVENT_STATE_COMPLETED = "completed"
