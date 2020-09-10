"""Frills."""

import json

from enum import IntEnum
from pprint import pformat
from time import time
from typing import Any


def ppjson(dumpit: Any, elide_to: int = None) -> str:
    """JSON pretty printer, whether already json-encoded or not."""

    if elide_to is not None:
        elide_to = max(elide_to, 3)  # make room for ellipses '...'
    try:
        rv = json.dumps(
            json.loads(dumpit) if isinstance(dumpit, str) else dumpit, indent=4
        )
    except TypeError:
        rv = "{}".format(pformat(dumpit, indent=4, width=120))
    return (
        rv
        if elide_to is None or len(rv) <= elide_to
        else "{}...".format(rv[0 : (elide_to - 3)])
    )


class Stopwatch:
    """Stopwatch class for troubleshooting lags."""

    def __init__(self, digits: int = None):
        """Instantiate and start."""

        self._mark = [time()] * 2
        self._digits = digits

    def mark(self, digits: int = None) -> float:
        """Return time in seconds since last mark, reset, or construction."""

        self._mark[:] = [self._mark[1], time()]
        rv = self._mark[1] - self._mark[0]

        if digits is not None and digits > 0:
            rv = round(rv, digits)
        elif digits == 0 or self._digits == 0:
            rv = int(rv)
        elif self._digits is not None and self._digits > 0:
            rv = round(rv, self._digits)

        return rv

    def reset(self) -> float:
        """Reset."""

        self._mark = [time()] * 2
        return 0.0


class Ink(IntEnum):
    """Class encapsulating ink colours for logging."""

    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37

    def __call__(self, message: str) -> str:
        """
        Return input message in colour.

        :return: input message in colour
        """

        return "\033[{}m{}\033[0m".format(self.value, message)
