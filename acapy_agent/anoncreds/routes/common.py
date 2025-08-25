"""Common definitions for AnonCreds routes."""

endorser_connection_id_description = (
    "Connection identifier (optional) (this is an example). "
    "You can set this if you know the endorser's connection id you want to use. "
    "If not specified then the agent will attempt to find an endorser connection."
)
create_transaction_for_endorser_description = (
    "Create transaction for endorser (optional, default false). "
    "Use this for agents who don't specify an author role but want to "
    "create a transaction for an endorser to sign."
)
