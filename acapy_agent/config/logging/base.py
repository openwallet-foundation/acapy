"""Base configurations and constants for logging."""

DEFAULT_LOGGING_CONFIG_PATH_INI = "acapy_agent.config.logging:default_logging_config.ini"
DEFAULT_MULTITENANT_LOGGING_CONFIG_PATH_INI = (
    "acapy_agent.config.logging:default_multitenant_logging_config.ini"
)
LOG_FORMAT_FILE_ALIAS_PATTERN = (
    "%(asctime)s %(wallet_id)s %(levelname)s %(pathname)s:%(lineno)d %(message)s"
)
