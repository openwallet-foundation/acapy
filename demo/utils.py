import asyncio
import os
from timeit import default_timer

import colored

import prompt_toolkit
from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop
from prompt_toolkit.patch_stdout import patch_stdout

COLORIZE = bool(os.getenv("COLORIZE")) or os.getenv("TERM") == "xterm"


def print_ext(*msg, color=None, prefix="", end=None, **kwargs):
    if color and COLORIZE:
        msg = (colored.stylize(m, colored.fg(color)) for m in msg)
    if prefix:
        msg = (f"{prefix:10s} |", *msg)
    print(*msg, end=end, **kwargs)


def output_reader(handle, callback, loop, *args, **kwargs):
    for line in iter(handle.readline, b""):
        if not line:
            break
        asyncio.run_coroutine_threadsafe(callback(line, *args), loop)


async def log_async(*msg, color="magenta", **kwargs):
    print_ext(*msg, color=color, **kwargs)


def log_msg(*msg, **kwargs):
    # try to synchronize messages with agent logs
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(log_async(*msg, **kwargs), loop)


def flatten(args):
    for arg in args:
        if isinstance(arg, (list, tuple)):
            yield from flatten(arg)
        else:
            yield arg


def prompt_init():
    if hasattr(prompt_init, "_called"):
        return
    prompt_init._called = True
    use_asyncio_event_loop()


async def prompt(*args, **kwargs):
    prompt_init()
    with patch_stdout():
        try:
            return await prompt_toolkit.prompt(*args, async_=True, **kwargs)
        except EOFError:
            return None


async def prompt_loop(*args, **kwargs):
    while True:
        option = await prompt(*args, **kwargs)
        yield option


class DurationTimer:
    def __init__(self, label: str = None, callback=None):
        self.callback = callback
        self.duration = None
        self.label = label
        self.last_error = None
        self.total = 0.0
        self.init_time = self.now()
        self.start_time = None
        self.stop_time = None
        self.running = False

    @classmethod
    def now(cls):
        return default_timer()

    def start(self):
        self.start_time = self.now()
        self.running = True

    def stop(self):
        if not self.running:
            return
        self.stop_time = self.now()
        self.duration = self.stop_time - self.start_time
        self.running = False
        self.total += self.duration
        if self.callback:
            self.callback(self)

    def cancel(self):
        self.running = False

    def reset(self):
        self.duration = None
        self.total = 0.0
        self.last_error = None
        restart = False
        if self.running:
            self.stop()
            restart = True
        self.start_time = None
        self.stop_time = None
        if restart:
            self.start()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, err_type, err_value, err_tb):
        self.last_error = err_value
        self.stop()


def log_timer(label: str, show: bool = True, logger=None, **kwargs):
    logger = logger or log_msg
    cb = (
        (
            lambda timer: timer.last_error
            or logger(timer.label, f"{timer.duration:.2f}s", **kwargs)
        )
        if show
        else None
    )
    return DurationTimer(label, cb)
