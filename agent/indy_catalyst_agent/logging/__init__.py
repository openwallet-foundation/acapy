from logging import getLogger
from logging.config import fileConfig
from os import path


class LoggingConfigurator:
    @classmethod
    def configure(cls, logging_config_path: str = None, log_level: str = None):
        if logging_config_path is not None:
            config_path = logging_config_path
        else:
            config_path = path.join(
                path.dirname(path.abspath(__file__)), "default_logging_config.ini"
            )

        fileConfig(config_path, disable_existing_loggers=True)

        if log_level:
            log_level = log_level.upper()
            print(log_level)
            getLogger().setLevel(log_level)
