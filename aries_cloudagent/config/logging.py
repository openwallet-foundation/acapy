"""Utilities related to logging."""
import asyncio
import importlib
import json
import logging
import os
import pkg_resources
import sys
from random import randint
import re
import time as mod_time
import traceback

from collections import OrderedDict
from datetime import date, datetime, time, timezone, timedelta
from inspect import istraceback
from io import TextIOWrapper
from logging.handlers import BaseRotatingHandler
from logging.config import fileConfig
from portalocker import lock, unlock, LOCK_EX
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, TextIO

from ..core.profile import Profile
from ..version import __version__
from ..wallet.base import BaseWallet, DIDInfo

from .banner import Banner
from .base import BaseSettings


DEFAULT_LOGGING_CONFIG_PATH = "aries_cloudagent.config:default_logging_config.ini"


def load_resource(path: str, encoding: str = None) -> TextIO:
    """
    Open a resource file located in a python package or the local filesystem.

    Args:
        path: The resource path in the form of `dir/file` or `package:dir/file`
    Returns:
        A file-like object representing the resource
    """
    components = path.rsplit(":", 1)
    try:
        if len(components) == 1:
            return open(components[0], encoding=encoding)
        else:
            bstream = pkg_resources.resource_stream(components[0], components[1])
            if encoding:
                return TextIOWrapper(bstream, encoding=encoding)
            return bstream
    except IOError:
        pass


class LoggingConfigurator:
    """Utility class used to configure logging and print an informative start banner."""

    @classmethod
    def configure(
        cls,
        logging_config_path: str = None,
        log_level: str = None,
        log_file: str = None,
    ):
        """
        Configure logger.

        :param logging_config_path: str: (Default value = None) Optional path to
            custom logging config

        :param log_level: str: (Default value = None)
        """
        if logging_config_path is not None:
            config_path = logging_config_path
        else:
            config_path = DEFAULT_LOGGING_CONFIG_PATH

        log_config = load_resource(config_path, "utf-8")
        if log_config:
            with log_config:
                fileConfig(log_config, disable_existing_loggers=False)
        else:
            logging.basicConfig(level=logging.WARNING)
            logging.root.warning(f"Logging config file not found: {config_path}")

        if log_file:
            logging.root.handlers.clear()
            logging.root.handlers.append(
                logging.FileHandler(log_file, encoding="utf-8")
            )

        if log_level:
            log_level = log_level.upper()
            logging.root.setLevel(log_level)

    @classmethod
    def print_banner(
        cls,
        agent_label,
        inbound_transports,
        outbound_transports,
        public_did,
        admin_server=None,
        banner_length=40,
        border_character=":",
    ):
        """
        Print a startup banner describing the configuration.

        Args:
            agent_label: Agent Label
            inbound_transports: Configured inbound transports
            outbound_transports: Configured outbound transports
            admin_server: Admin server info
            public_did: Public DID
            banner_length: (Default value = 40) Length of the banner
            border_character: (Default value = ":") Character to use in banner
            border
        """
        print()
        banner = Banner(border=border_character, length=banner_length)
        banner.print_border()

        # Title
        banner.print_title(agent_label or "ACA")

        banner.print_spacer()
        banner.print_spacer()

        # Inbound transports
        banner.print_subtitle("Inbound Transports")
        internal_in_transports = [
            f"{transport.scheme}://{transport.host}:{transport.port}"
            for transport in inbound_transports.values()
            if not transport.is_external
        ]
        if internal_in_transports:
            banner.print_spacer()
            banner.print_list(internal_in_transports)
            banner.print_spacer()
        external_in_transports = [
            f"{transport.scheme}://{transport.host}:{transport.port}"
            for transport in inbound_transports.values()
            if transport.is_external
        ]
        if external_in_transports:
            banner.print_spacer()
            banner.print_subtitle("  External Plugin")
            banner.print_spacer()
            banner.print_list(external_in_transports)
            banner.print_spacer()

        # Outbound transports
        banner.print_subtitle("Outbound Transports")
        internal_schemes = set().union(
            *(
                transport.schemes
                for transport in outbound_transports.values()
                if not transport.is_external
            )
        )
        if internal_schemes:
            banner.print_spacer()
            banner.print_list([f"{scheme}" for scheme in sorted(internal_schemes)])
            banner.print_spacer()

        external_schemes = set().union(
            *(
                transport.schemes
                for transport in outbound_transports.values()
                if transport.is_external
            )
        )
        if external_schemes:
            banner.print_spacer()
            banner.print_subtitle("  External Plugin")
            banner.print_spacer()
            banner.print_list([f"{scheme}" for scheme in sorted(external_schemes)])
            banner.print_spacer()

        # DID info
        if public_did:
            banner.print_subtitle("Public DID Information")
            banner.print_spacer()
            banner.print_list([f"DID: {public_did}"])
            banner.print_spacer()

        # Admin server info
        banner.print_subtitle("Administration API")
        banner.print_spacer()
        banner.print_list(
            [f"http://{admin_server.host}:{admin_server.port}"]
            if admin_server
            else ["not enabled"]
        )
        banner.print_spacer()

        banner.print_version(__version__)

        banner.print_border()
        print()
        print("Listening...")
        print()


######################################################################
# Derived from
# https://github.com/python/cpython/blob/main/Lib/logging/handlers.py
# and https://github.com/yorks/mpfhandler/blob/master/src/mpfhandler.py
######################################################################
class TimedRotatingFileMultiProcessHandler(BaseRotatingHandler):
    """
    Handler for logging to a file.

    Rotating the log file at certain timed with file lock unlock
    mechanism to support multi-process writing to log file.
    """

    def __init__(
        self,
        filename,
        when="h",
        interval=1,
        backupCount=1,
        encoding=None,
        delay=False,
        utc=False,
        atTime=None,
    ):
        """
        Initialize an instance of `TimedRotatingFileMultiProcessHandler`.

        Args:
            filename: log file name with path
            when: specify when to rotate log file
            interval: interval when to rotate
            backupCount: count of backup file, backupCount of 0 will mean
                no limit on count of backup file [no backup will be deleted]

        """
        BaseRotatingHandler.__init__(
            self,
            filename,
            "a",
            encoding=encoding,
            delay=delay,
        )
        self.when = when.upper()
        self.backupCount = backupCount
        self.utc = utc
        self.atTime = atTime
        self.mylogfile = "%s.%08d" % ("/tmp/trfmphanldler", randint(0, 99999999))
        self.interval = interval

        if self.when == "S":
            self.interval = 1
            self.suffix = "%Y-%m-%d_%H-%M-%S"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}(\.\w+)?$"
        elif self.when == "M":
            self.interval = 60
            self.suffix = "%Y-%m-%d_%H-%M"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}(\.\w+)?$"
        elif self.when == "H":
            self.interval = 60 * 60
            self.suffix = "%Y-%m-%d_%H"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}_\d{2}(\.\w+)?$"
        elif self.when == "D" or self.when == "MIDNIGHT":
            self.interval = 60 * 60 * 24
            self.suffix = "%Y-%m-%d"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}(\.\w+)?$"
        elif self.when.startswith("W"):
            self.interval = 60 * 60 * 24 * 7
            if len(self.when) != 2:
                raise ValueError(
                    "You must specify a day for weekly rollover from 0 "
                    "to 6 (0 is Monday): %s" % self.when
                )
            if self.when[1] < "0" or self.when[1] > "6":
                raise ValueError(
                    "Invalid day specified for weekly rollover: %s" % self.when
                )
            self.dayOfWeek = int(self.when[1])
            self.suffix = "%Y-%m-%d"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}(\.\w+)?$"
        else:
            raise ValueError("Invalid rollover interval specified: %s" % self.when)

        self.extMatch = re.compile(self.extMatch, re.ASCII)
        self.interval = self.interval * interval
        self.stream_lock = None
        self.lock_file = self._getLockFile()
        self.next_rollover_time = self.get_next_rollover_time()
        if not self.next_rollover_time:
            self.next_rollover_time = self.compute_next_rollover_time()
            self.save_next_rollover_time()

    def _log2mylog(self, msg):
        """Write to external log file."""
        time_str = mod_time.strftime(
            "%Y-%m-%d %H:%M:%S", mod_time.localtime(mod_time.time())
        )
        msg = str(msg)
        content = "%s [%s]\n" % (time_str, msg)
        fa = open(self.mylogfile, "a")
        fa.write(content)
        fa.close()

    def _getLockFile(self):
        """Return log lock file."""
        if self.baseFilename.endswith(".log"):
            lock_file = self.baseFilename[:-4]
        else:
            lock_file = self.baseFilename
        lock_file += ".lock"
        return lock_file

    def _openLockFile(self):
        """Open log lock file."""
        lock_file = self._getLockFile()
        self.stream_lock = open(lock_file, "w")

    def compute_next_rollover_time(self):
        """Return next rollover time."""
        next_time = None
        current_datetime = datetime.now()
        if self.when == "D":
            next_datetime = current_datetime + timedelta(days=self.interval)
            next_date = next_datetime.date()
            next_time = int(mod_time.mktime(next_date.timetuple()))
        elif self.when.startswith("W"):
            days = 0
            current_weekday = current_datetime.weekday()
            if current_weekday == self.dayOfWeek:
                days = self.interval + 7
            elif current_weekday < self.dayOfWeek:
                days = self.dayOfWeek - current_weekday
            else:
                days = 6 - current_weekday + self.dayOfWeek + 1
            next_datetime = current_datetime + timedelta(days=days)
            next_date = next_datetime.date()
            next_time = int(mod_time.mktime(next_date.timetuple()))
        else:
            tmp_next_datetime = current_datetime + timedelta(seconds=self.interval)
            next_datetime = tmp_next_datetime.replace(microsecond=0)
            if self.when == "H":
                next_datetime = tmp_next_datetime.replace(
                    minute=0, second=0, microsecond=0
                )
            elif self.when == "M":
                next_datetime = tmp_next_datetime.replace(second=0, microsecond=0)
            next_time = int(mod_time.mktime(next_datetime.timetuple()))
        return next_time

    def get_next_rollover_time(self):
        """Get next rollover time stamp from lock file."""
        try:
            fp = open(self.lock_file, "r")
            c = fp.read()
            fp.close()
            return int(c)
        except Exception:
            return False

    def save_next_rollover_time(self):
        """Save the nextRolloverTimestamp to lock file."""
        if not self.next_rollover_time:
            return 0
        content = "%d" % self.next_rollover_time
        if not self.stream_lock:
            self._openLockFile()
        lock(self.stream_lock, LOCK_EX)
        try:
            self.stream_lock.seek(0)
            self.stream_lock.write(content)
            self.stream_lock.flush()
        except Exception:
            pass
        finally:
            unlock(self.stream_lock)

    def acquire(self):
        """Acquire thread and file locks."""
        BaseRotatingHandler.acquire(self)
        if self.stream_lock:
            if self.stream_lock.closed:
                try:
                    self._openLockFile()
                except Exception:
                    self.stream_lock = None
                    return
            lock(self.stream_lock, LOCK_EX)

    def release(self):
        """Release file and thread locks."""
        try:
            if self.stream_lock and not self.stream_lock.closed:
                unlock(self.stream_lock)
        except Exception:
            pass
        finally:
            BaseRotatingHandler.release(self)

    def _close_stream(self):
        """Close the log file stream."""
        if self.stream:
            try:
                if not self.stream.closed:
                    self.stream.flush()
                    self.stream.close()
            finally:
                self.stream = None

    def _close_stream_lock(self):
        """Close the lock file stream."""
        if self.stream_lock:
            try:
                if not self.stream_lock.closed:
                    self.stream_lock.flush()
                    self.stream_lock.close()
            finally:
                self.stream_lock = None

    def close(self):
        """Close log stream and stream_lock."""
        try:
            self._close_stream()
            self._close_stream_lock()
        finally:
            self.stream = None
            self.stream_lock = None

    def get_log_files_to_delete(self):
        """Delete backup files on rotation based on backupCount."""
        dir_name, base_name = os.path.split(self.baseFilename)
        file_names = os.listdir(dir_name)
        result = []
        n, e = os.path.splitext(base_name)
        prefix = n + "."
        plen = len(prefix)
        for file_name in file_names:
            if self.namer is None:
                if not file_name.startswith(base_name):
                    continue
            else:
                if (
                    not file_name.startswith(base_name)
                    and file_name.endswith(e)
                    and len(file_name) > (plen + 1)
                    and not file_name[plen + 1].isdigit()
                ):
                    continue
            if file_name[:plen] == prefix:
                suffix = file_name[plen:]
                parts = suffix.split(".")
                for part in parts:
                    if self.extMatch.match(part):
                        result.append(os.path.join(dir_name, file_name))
                        break
        if len(result) < self.backupCount:
            result = []
        else:
            result.sort()
            result = result[: len(result) - self.backupCount]
        return result

    def shouldRollover(self, record):
        """Determine if rollover should occur."""
        t = int(mod_time.time())
        if t >= self.next_rollover_time:
            return 1
        return 0

    def doRollover(self):
        """Perform rollover."""
        self._close_stream()
        self.acquire()
        try:
            file_next_rollover_time = self.get_next_rollover_time()
            if not file_next_rollover_time:
                self.release()
                return 0
            if self.next_rollover_time < file_next_rollover_time:
                self.next_rollover_time = file_next_rollover_time
                self.release()
                return 0
        except Exception:
            pass
        time_tuple = mod_time.localtime(self.next_rollover_time - 1)
        dfn = self.baseFilename + "." + mod_time.strftime(self.suffix, time_tuple)
        if os.path.exists(dfn):
            bakname = dfn + ".bak"
            while os.path.exists(bakname):
                bakname = "%s.%08d" % (bakname, randint(0, 99999999))
            try:
                os.rename(dfn, bakname)
            except Exception:
                pass
        if os.path.exists(self.baseFilename):
            try:
                os.rename(self.baseFilename, dfn)
            except Exception:
                pass
        self.next_rollover_time = self.compute_next_rollover_time()
        self.save_next_rollover_time()
        if self.backupCount > 0:
            for s in self.get_log_files_to_delete():
                os.remove(s)
        if not self.delay:
            self.stream = self._open()
        self.release()


######################################################################
# Derived from
# https://github.com/madzak/python-json-logger/blob/master/src/
# pythonjsonlogger/jsonlogger.py
######################################################################
RESERVED_ATTRS: Tuple[str, ...] = (
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
)


def merge_record_extra(
    record: logging.LogRecord,
    target: Dict,
    reserved: Union[Dict, List],
    rename_fields: Optional[Dict[str, str]] = None,
) -> Dict:
    """
    Merge extra attrib from LogRecord into target dictionary.

    :param record: logging.LogRecord
    :param target: dict to update
    :param reserved: dict or list with reserved keys to skip
    :param rename_fields: an optional dict, used to rename
        field names in the output.
    """
    if rename_fields is None:
        rename_fields = {}
    for key, value in record.__dict__.items():
        # this allows to have numeric keys
        if key not in reserved and not (
            hasattr(key, "startswith") and key.startswith("_")
        ):
            target[rename_fields.get(key, key)] = value
    return target


class JsonEncoder(json.JSONEncoder):
    """Custom JSONEncoder."""

    def default(self, obj):
        """Return a serializable object or calls the base implementation."""
        if isinstance(obj, (date, datetime, time)):
            return self.format_datetime_obj(obj)

        elif istraceback(obj):
            return "".join(traceback.format_tb(obj)).strip()

        elif type(obj) == Exception or isinstance(obj, Exception) or type(obj) == type:
            return str(obj)

        try:
            return super(JsonEncoder, self).default(obj)

        except TypeError:
            try:
                return str(obj)

            except Exception:
                return None

    def format_datetime_obj(self, obj):
        """Return formatted datetime object."""
        return obj.isoformat()


class CustomJsonFormatter(logging.Formatter):
    """Custom logging JSONFormatter."""

    def __init__(
        self,
        *args: Any,
        json_default: Optional[Union[Callable, str]] = None,
        json_encoder: Optional[Union[Callable, str]] = None,
        json_serialiser: Union[Callable, str] = json.dumps,
        json_indent: Optional[Union[int, str]] = None,
        json_ensure_ascii: bool = True,
        prefix: str = "",
        rename_fields: Optional[dict] = None,
        static_fields: Optional[dict] = None,
        reserved_attrs: Tuple[str, ...] = RESERVED_ATTRS,
        timestamp: Union[bool, str] = False,
        **kwargs: Any,
    ):
        """Initialize an instance of `CustomJsonFormatter`."""
        self.json_default = self._str_to_fn(json_default)
        self.json_encoder = self._str_to_fn(json_encoder)
        self.json_serializer = self._str_to_fn(json_serialiser)
        self.json_indent = json_indent
        self.json_ensure_ascii = json_ensure_ascii
        self.prefix = prefix
        self.rename_fields = rename_fields or {}
        self.static_fields = static_fields or {}
        self.reserved_attrs = dict(zip(reserved_attrs, reserved_attrs))
        self.timestamp = timestamp

        logging.Formatter.__init__(self, *args, **kwargs)
        if not self.json_encoder and not self.json_default:
            self.json_encoder = JsonEncoder

        self._required_fields = self.parse()
        self._skip_fields = dict(zip(self._required_fields, self._required_fields))
        self._skip_fields.update(self.reserved_attrs)

    def _str_to_fn(self, fn_as_str):
        """Parse string as package.module.function and return function."""
        if not isinstance(fn_as_str, str):
            return fn_as_str

        path, _, function = fn_as_str.rpartition(".")
        module = importlib.import_module(path)
        return getattr(module, function)

    def parse(self) -> List[str]:
        """Parse format string looking for substitutions."""
        if isinstance(self._style, logging.StringTemplateStyle):
            formatter_style_pattern = re.compile(r"\$\{(.+?)\}", re.IGNORECASE)
        elif isinstance(self._style, logging.StrFormatStyle):
            formatter_style_pattern = re.compile(r"\{(.+?)\}", re.IGNORECASE)
        elif isinstance(self._style, logging.PercentStyle):
            formatter_style_pattern = re.compile(r"%\((.+?)\)", re.IGNORECASE)
        else:
            raise ValueError("Invalid format: %s" % self._fmt)

        if self._fmt:
            return formatter_style_pattern.findall(self._fmt)
        else:
            return []

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add fields, overwriting logic provided in logging.Formatter."""
        for field in self._required_fields:
            log_record[field] = record.__dict__.get(field)

        log_record.update(self.static_fields)
        log_record.update(message_dict)
        merge_record_extra(
            record,
            log_record,
            reserved=self._skip_fields,
            rename_fields=self.rename_fields,
        )

        if self.timestamp:
            key = self.timestamp if type(self.timestamp) == str else "timestamp"
            log_record[key] = datetime.fromtimestamp(record.created, tz=timezone.utc)

        self._perform_rename_log_fields(log_record)

    def _perform_rename_log_fields(self, log_record):
        for old_field_name, new_field_name in self.rename_fields.items():
            log_record[new_field_name] = log_record[old_field_name]
            del log_record[old_field_name]

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record and serializes to json."""
        message_dict: Dict[str, Any] = {}
        if isinstance(record.msg, dict):
            message_dict = record.msg
            record.message = ""
        else:
            record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)
        if record.exc_info and not message_dict.get("exc_info"):
            message_dict["exc_info"] = self.formatException(record.exc_info)
        if not message_dict.get("exc_info") and record.exc_text:
            message_dict["exc_info"] = record.exc_text
        if record.stack_info and not message_dict.get("stack_info"):
            message_dict["stack_info"] = self.formatStack(record.stack_info)

        log_record = OrderedDict()
        self.add_fields(log_record, record, message_dict)

        return self.json_serializer(
            log_record,
            default=self.json_default,
            cls=self.json_encoder,
            indent=self.json_indent,
            ensure_ascii=self.json_ensure_ascii,
        )


LOG_FORMAT_FILE_ALIAS = CustomJsonFormatter(
    "%(asctime)s [%(public_did)s] %(levelname)s %(filename)s %(lineno)d %(message)s"
)
LOG_FORMAT_FILE_NO_ALIAS = CustomJsonFormatter(
    "%(asctime)s %(levelname)s %(filename)s %(lineno)d %(message)s"
)
LOG_FORMAT_STREAM = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(lineno)d %(message)s"
)


def clear_prev_handlers(logger: logging.Logger) -> logging.Logger:
    """Remove all handler classes associated with logger instance."""
    iter_count = 0
    num_handlers = len(logger.handlers)
    while iter_count < num_handlers:
        logger.removeHandler(logger.handlers[0])
        iter_count = iter_count + 1
    return logger


def get_logger_inst(profile: Profile, logger_name) -> logging.Logger:
    """Return a logger instance with provided name and handlers."""
    logger = None
    loop = asyncio.get_event_loop()
    public_did_ident = loop.run_until_complete(get_public_did_ident(profile))
    if public_did_ident:
        logger = get_logger_with_handlers(
            settings=profile.settings,
            logger=logging.getLogger(f"{logger_name}_{public_did_ident}"),
            public_did_ident=public_did_ident,
            interval=profile.settings.get("log.handler_interval") or 7,
            backup_count=profile.settings.get("log.handler_bakcount") or 1,
            at_when=profile.settings.get("log.handler_when") or "d",
        )
    else:
        logger = get_logger_with_handlers(
            settings=profile.settings,
            logger=logging.getLogger(logger_name),
            interval=profile.settings.get("log.handler_interval") or 7,
            backup_count=profile.settings.get("log.handler_bakcount") or 1,
            at_when=profile.settings.get("log.handler_when") or "d",
        )
    return logger


async def get_public_did_ident(profile: Profile) -> Optional[str]:
    """Get public did identifier for logging, if applicable."""
    if profile.settings.get("log.file"):
        async with profile.session() as session:
            wallet = session.inject(BaseWallet)
            req_did_info: DIDInfo = await wallet.get_public_did()
            if not req_did_info:
                req_did_info: DIDInfo = (await wallet.get_local_dids())[0]
            return req_did_info.did
    else:
        return None


def get_logger_with_handlers(
    settings: BaseSettings,
    logger: logging.Logger,
    at_when: str = None,
    interval: int = None,
    backup_count: int = None,
    public_did_ident: str = None,
) -> logging.Logger:
    """Return logger instance with necessary handlers if required."""
    if settings.get("log.file"):
        # Clear handlers set previously for this logger instance
        logger = clear_prev_handlers(logger)
        # log file handler
        file_path = settings.get("log.file")
        file_handler = TimedRotatingFileMultiProcessHandler(
            filename=file_path,
            interval=interval,
            when=at_when,
            backupCount=backup_count,
        )
        if public_did_ident:
            file_handler.setFormatter(LOG_FORMAT_FILE_ALIAS)
        else:
            file_handler.setFormatter(LOG_FORMAT_FILE_NO_ALIAS)
        logger.addHandler(file_handler)
        # stream console handler
        std_out_handler = logging.StreamHandler(sys.stdout)
        std_out_handler.setFormatter(LOG_FORMAT_STREAM)
        logger.addHandler(std_out_handler)
        if public_did_ident:
            logger = logging.LoggerAdapter(logger, {"public_did": public_did_ident})
        # set log level
        logger_level = (
            (settings.get("log.level")).upper()
            if settings.get("log.level")
            else logging.INFO
        )
        logger.setLevel(logger_level)
    return logger
