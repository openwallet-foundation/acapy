"""Timed rotating file handler for aca-py agent."""

import logging
import os
import re
import time as mod_time
from datetime import datetime, timedelta
from logging.handlers import BaseRotatingHandler
from random import randint

from portalocker import LOCK_EX, lock, unlock


class TimedRotatingFileMultiProcessHandler(BaseRotatingHandler):
    """Handler for logging to a file with timed rotation and multi-process support.

    Derived from Python's `logging.handlers` and custom implementations to handle
    multi-process scenarios.

    This implementation is based on Python's built-in logging handlers and the mpfhandler
    library, but includes custom modifications to properly handle interval, backupCount,
    and deletion of old backup files during rotation in multi-process scenarios.

    References:
        - https://github.com/python/cpython/blob/main/Lib/logging/handlers.py
        - https://github.com/yorks/mpfhandler/blob/master/src/mpfhandler.py
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
        """Initialize an instance of `TimedRotatingFileMultiProcessHandler`.

        Args:
            filename (str): The log file name with path.
            when (str, optional): Specifies when to rotate the log file. Defaults to "h".
            interval (int, optional): The interval when to rotate. Defaults to 1.
            backupCount (int, optional): The count of backup files. A backupCount of 0
                means no limit on the count of backup files (no backup will be deleted).
                Defaults to 1.
            encoding (str, optional): The encoding to use for the log file.
                Defaults to None.
            delay (bool, optional): Whether to delay file opening until the first log
                message is emitted. Defaults to False.
            utc (bool, optional): Whether to use UTC time for log rotation.
                Defaults to False.
            atTime (datetime.time, optional): The specific time at which log rotation
                should occur. Defaults to None.

        Raises:
            ValueError: If an invalid rollover interval is specified.

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

        # Set the appropriate suffix and regular expression pattern based on the specified rollover interval # noqa: E501
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


logging.handlers.TimedRotatingFileMultiProcessHandler = (
    TimedRotatingFileMultiProcessHandler
)
