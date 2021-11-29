# Logging docs

Acapy supports multiple configurations of logging.

## Log level

Acapy's logging is based on python's [logging lib](https://docs.python.org/3/howto/logging.html).
Log levels `DEBUG`, `INFO` and `WARNING` are available.
Other log levels fall back to `WARNING`.

## Command Line Arguments

* `--log-level` - The log level to log on std out.
* `--log-file` - Path to a file to log to.

Example:

```sh
./bin/aca-py start --log-level debug --log-file acapy.log
```

## Environment Variables

The log level can be configured using the environment variable `ACAPY_LOG_LEVEL`.
The log file can be set by `ACAPY_LOG_FILE`.
The log config can be set by `ACAPY_LOG_CONFIG`.

Example:

```sh
ACAPY_LOG_LEVEL=info ACAPY_LOG_FILE=./acapy.log ACAPY_LOG_CONFIG=./acapy_log.ini ./bin/aca-py start
```

## Acapy Config File

Following parameters can be used in a configuration file like [this](demo/demo-args.yaml).

```yaml
log-level: WARNING
debug-connections: false
debug-presentations: false
```

Warning: debug-connections and debug-presentations must not be used in a production environment as they log also credential claims values.
Both parameters are independent of the log level, which means:
Also if log-level is set to WARNING, connections and presentations will be logged like in debug log level.

## Log config file

Find an example in [default_logging_config.ini](aries_cloudagent/config/default_logging_config.ini).

You can find more detail description in the [logging documentation](https://docs.python.org/3/howto/logging.html#configuring-logging).
