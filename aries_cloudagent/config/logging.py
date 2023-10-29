"""Utilities related to logging."""
import asyncio
from datetime import datetime, timedelta
from io import TextIOWrapper
import logging
from logging.config import fileConfig
from logging.handlers import BaseRotatingHandler
import os
from random import randint
import re
import sys
import time as mod_time
from typing import Optional, TextIO

import pkg_resources
from portalocker import LOCK_EX, lock, unlock
from pythonjsonlogger import jsonlogger

from ..config.settings import Settings
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
        with Banner(border=border_character, length=banner_length) as banner:
            # Title
            banner.title(agent_label or "ACA")
            # Inbound transports
            banner.subtitle("Inbound Transports")
            internal_in_transports = [
                f"{transport.scheme}://{transport.host}:{transport.port}"
                for transport in inbound_transports.values()
                if not transport.is_external
            ]
            if internal_in_transports:
                banner.list(internal_in_transports)
            external_in_transports = [
                f"{transport.scheme}://{transport.host}:{transport.port}"
                for transport in inbound_transports.values()
                if transport.is_external
            ]
            if external_in_transports:
                banner.subtitle("  External Plugin")
                banner.list(external_in_transports)

            # Outbound transports
            banner.subtitle("Outbound Transports")
            internal_schemes = set().union(
                *(
                    transport.schemes
                    for transport in outbound_transports.values()
                    if not transport.is_external
                )
            )
            if internal_schemes:
                banner.list([f"{scheme}" for scheme in sorted(internal_schemes)])

            external_schemes = set().union(
                *(
                    transport.schemes
                    for transport in outbound_transports.values()
                    if transport.is_external
                )
            )
            if external_schemes:
                banner.subtitle("  External Plugin")
                banner.list([f"{scheme}" for scheme in sorted(external_schemes)])

            # DID info
            if public_did:
                banner.subtitle("Public DID Information")
                banner.list([f"DID: {public_did}"])

            # Admin server info
            banner.subtitle("Administration API")
            banner.list(
                [f"http://{admin_server.host}:{admin_server.port}"]
                if admin_server
                else ["not enabled"]
            )

            banner.version(__version__)

        print()
        print("Listening...")
        print()

    @classmethod
    def print_notices(cls, settings: Settings):
        """Print notices and warnings."""
        if settings.get("wallet.type", "in_memory").lower() == "indy":
            with Banner(border=":", length=80, file=sys.stderr) as banner:
                banner.centered("⚠ DEPRECATION NOTICE: ⚠")
                banner.hr()
                banner.print(
                    "The Indy wallet type is deprecated, use Askar instead; see: "
                    "https://aca-py.org/main/deploying/IndySDKtoAskarMigration/",
                )
            print()


######################################################################
# Derived from
# https://github.com/python/cpython/blob/main/Lib/logging/handlers.py
# and https://github.com/yorks/mpfhandler/blob/master/src/mpfhandler.py
#
# interval and backupCount are not working as intended in mpfhandler
# library. Also the old backup files were not being deleted on rotation.
# This required the following custom implementation.
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


LOG_FORMAT_FILE_ALIAS_PATTERN = (
    "%(asctime)s [%(did)s] %(levelname)s %(filename)s %(lineno)d %(message)s"
)

LOG_FORMAT_FILE_NO_ALIAS_PATTERN = (
    "%(asctime)s %(levelname)s %(filename)s %(lineno)d %(message)s"
)

LOG_FORMAT_STREAM_PATTERN = (
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
    did_ident = get_did_ident(profile)
    if did_ident:
        logger_name = f"{logger_name}_{did_ident}"
    return get_logger_with_handlers(
        settings=profile.settings,
        logger=logging.getLogger(logger_name),
        did_ident=did_ident,
        interval=profile.settings.get("log.handler_interval") or 7,
        backup_count=profile.settings.get("log.handler_bakcount") or 1,
        at_when=profile.settings.get("log.handler_when") or "d",
    )


def get_did_ident(profile: Profile) -> Optional[str]:
    """Get public did identifier for logging, if applicable."""
    did_ident = None
    if profile.settings.get("log.file"):

        async def _fetch_did() -> Optional[str]:
            async with profile.session() as session:
                wallet = session.inject(BaseWallet)
                req_did_info: DIDInfo = await wallet.get_public_did()
                if not req_did_info:
                    req_did_info: DIDInfo = (await wallet.get_local_dids())[0]
                if req_did_info:
                    did_ident = req_did_info.did
                return did_ident

        loop = asyncio.get_event_loop()
        did_ident = loop.run_until_complete(_fetch_did())
    return did_ident


def get_logger_with_handlers(
    settings: BaseSettings,
    logger: logging.Logger,
    at_when: str = None,
    interval: int = None,
    backup_count: int = None,
    did_ident: str = None,
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
        if did_ident:
            if settings.get("log.json_fmt"):
                file_handler.setFormatter(
                    jsonlogger.JsonFormatter(
                        settings.get("log.fmt_pattern") or LOG_FORMAT_FILE_ALIAS_PATTERN
                    )
                )
            else:
                file_handler.setFormatter(
                    logging.Formatter(
                        settings.get("log.fmt_pattern") or LOG_FORMAT_FILE_ALIAS_PATTERN
                    )
                )
        else:
            if settings.get("log.json_fmt"):
                file_handler.setFormatter(
                    jsonlogger.JsonFormatter(
                        settings.get("log.fmt_pattern")
                        or LOG_FORMAT_FILE_NO_ALIAS_PATTERN
                    )
                )
            else:
                file_handler.setFormatter(
                    logging.Formatter(
                        settings.get("log.fmt_pattern")
                        or LOG_FORMAT_FILE_NO_ALIAS_PATTERN
                    )
                )
        logger.addHandler(file_handler)
        # stream console handler
        std_out_handler = logging.StreamHandler(sys.stdout)
        std_out_handler.setFormatter(
            logging.Formatter(
                settings.get("log.fmt_pattern") or LOG_FORMAT_STREAM_PATTERN
            )
        )
        logger.addHandler(std_out_handler)
        if did_ident:
            logger = logging.LoggerAdapter(logger, {"did": did_ident})
    # set log level
    logger_level = (
        (settings.get("log.level")).upper()
        if settings.get("log.level")
        else logging.INFO
    )
    logger.setLevel(logger_level)
    return logger
