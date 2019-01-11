from os import path
from logging.config import fileConfig


class LoggingConfigurator:
    @classmethod
    def configure(cls, logging_config_path=None):
        if logging_config_path is not None:
            config_path = logging_config_path
        else:
            config_path = path.join(
                path.dirname(path.abspath(__file__)), "default_logging_config.ini"
            )

        fileConfig(config_path, disable_existing_loggers=False)
