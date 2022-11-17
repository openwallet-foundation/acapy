"""Classes for tracking performance and timing."""

import functools
import inspect
import time
from typing import Sequence, TextIO, Union


class Stats:
    """A collection of statistics."""

    def __init__(self):
        """Initialize the Stats instance."""
        self.counts = {}
        self.max_time = {}
        self.min_time = {}
        self.total_time = {}

    def log(self, name: str, duration: float):
        """Log an entry in the stats."""
        if name in self.counts:
            self.counts[name] += 1
            self.max_time[name] = max(self.max_time[name], duration)
            self.min_time[name] = min(self.min_time[name], duration)
            self.total_time[name] += duration
        else:
            self.counts[name] = 1
            self.max_time[name] = duration
            self.min_time[name] = duration
            self.total_time[name] = duration

    def extract(self, names: Sequence[str] = None) -> dict:
        """Summarize the stats in a dictionary."""
        counts = self.counts.copy()
        all_names = set(counts)
        if names is None:
            names = all_names
            maxes = self.max_time.copy()
            mins = self.min_time.copy()
            totals = self.total_time.copy()
        else:
            names = set(names).intersection(all_names)
            counts = {name: val for (name, val) in counts.items() if name in names}
            maxes = {
                name: val for (name, val) in self.max_time.items() if name in names
            }
            mins = {name: val for (name, val) in self.min_time.items() if name in names}
            totals = {
                name: val for (name, val) in self.total_time.items() if name in names
            }

        return {
            "avg": {name: totals[name] / counts[name] for name in names},
            "count": counts,
            "max": maxes,
            "min": mins,
            "total": totals,
        }


class Timer:
    """Timer instance for a running task."""

    def __init__(self, collector: "Collector", groups: Sequence[str]):
        """Initialize the Timer instance."""
        self.collector = collector
        self.groups = groups
        self.start_time = None

    @classmethod
    def now(cls):
        """Fetch a standard timer value."""
        return time.perf_counter()

    def start(self) -> "Timer":
        """Start the timer."""
        self.start_time = self.now()
        return self

    def stop(self):
        """Stop the timer."""
        if self.start_time:
            dur = self.now() - self.start_time
            for grp in self.groups:
                self.collector.log(grp, dur, self.start_time)
        self.start_time = None

    def __enter__(self):
        """Enter the context manager."""
        return self.start()

    def __exit__(self, type, value, tb):
        """Exit the context manager."""
        self.stop()


class Collector:
    """Collector for a set of statistics."""

    def __init__(self, *, enabled: bool = True, log_path: str = None):
        """Initialize the Collector instance."""
        self._enabled = enabled
        self._log_file: TextIO = None
        self._log_path = log_path
        self._stats = None
        self.reset()

    def reset(self):
        """Reset the collector's statistics."""
        self._stats = Stats()
        if self._log_file:
            self._log_file.close()
            self._log_file = None
        if self._log_path:
            self._log_file = open(self._log_path, "w")

    @property
    def enabled(self) -> bool:
        """Accessor for the collector's enabled property."""
        return self._enabled

    @enabled.setter
    def enabled(self, val: bool):
        """Setter for the collector's enabled property."""
        self._enabled = val

    def log(self, name: str, duration: float, start: float = None):
        """Log an entry in the statistics if the collector is enabled."""
        if self._enabled:
            self._stats.log(name, duration)
            if self._log_file:
                if start is None:
                    start = time.perf_counter() - duration
                self._log_file.write(f"{name} {start:.5f} {duration:.5f}\n")

    def mark(self, *names):
        """Make a custom decorator function for adding to the set of groups."""
        return lambda fn: self(fn, names)

    def wrap(
        self,
        obj,
        prop_name: Union[str, Sequence[str]],
        groups: Sequence[str] = None,
        *,
        ignore_missing: bool = False,
    ):
        """Wrap a method on a class or class instance."""
        if not prop_name:
            raise ValueError("missing prop_name")
        if isinstance(prop_name, str):
            method = getattr(obj, prop_name, None)
            if method:
                setattr(obj, prop_name, self(method, groups))
            elif not ignore_missing:
                raise AttributeError(prop_name)
        else:
            for prop in prop_name:
                self.wrap(obj, prop, groups)

    def wrap_fn(self, fn, groups: Sequence[str]):
        """Wrap a function instance to collect timing statistics on execution."""

        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            with self.timer(*groups):
                result = fn(*args, **kwargs)
            return result

        return wrapped

    def wrap_coro(self, fn, groups: Sequence[str]):
        """Wrap a coroutine instance to collect timing statistics on execution."""

        @functools.wraps(fn)
        async def wrapped(*args, **kwargs):
            with self.timer(*groups):
                result = await fn(*args, **kwargs)
            return result

        return wrapped

    def __call__(self, fn, groups: Sequence[str] = None):
        """
        Decorate a function or class method.

        Returns: a wrapped function or coroutine with automatic stats collection
        """
        groups = set(groups) if groups else set()
        if inspect.iscoroutinefunction(fn):
            groups.add(fn.__qualname__)
            return self.wrap_coro(fn, groups)
        elif inspect.isfunction(fn) or inspect.ismethod(fn):
            groups.add(fn.__qualname__)
            return self.wrap_fn(fn, groups)
        else:
            raise ValueError(f"Expected function or coroutine, got: {fn}")

    def timer(self, *groups):
        """Create a new timer attached to this collector."""
        return Timer(self, groups)

    @property
    def results(self) -> dict:
        """Accessor for the current set of collected statistics."""
        return self._stats.extract()

    def extract(self, groups: Sequence[str] = None) -> dict:
        """Extract statistics for a specific set of groups."""
        return self._stats.extract(groups)
