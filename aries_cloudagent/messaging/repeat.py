"""Utils for repeating tasks."""

import asyncio

import async_timeout


class RepeatAttempt:
    """Represents the current iteration in a repeat sequence."""

    def __init__(self, seq: "RepeatSequence", index: int = 1):
        """Initialize the attempt instance."""
        self.index = index
        self.seq = seq

    def next(self) -> "RepeatAttempt":
        """Get the next attempt instance."""
        if self.final:
            raise StopIteration
        self.index += 1
        return self

    async def __anext__(self) -> "RepeatAttempt":
        """Implement async iterator protocol to wait between attempts."""
        if not self.index:
            self.index = 1
            return self
        else:
            if self.final:
                raise StopAsyncIteration
            interval = self.next_interval
            if interval:
                await asyncio.sleep(interval)
            self.index += 1
            return self

    @property
    def final(self) -> bool:
        """Check if this is the last instance in the sequence."""
        return bool(self.seq.limit and self.index >= self.seq.limit)

    @property
    def next_interval(self) -> float:
        """Calculate the interval before the next attempt."""
        return self.seq.next_interval(self.index)

    def timeout(self, interval: float = None):
        """Create a context manager for timing out an attempt."""
        return async_timeout.timeout(
            self.next_interval if interval is None else interval
        )

    def __repr__(self) -> str:
        """Format as a string for debugging."""
        return f"<{self.__class__.__name__} index={self.index} seq={self.seq}>"


class RepeatSequence:
    """Represents a repetition sequence."""

    def __init__(self, limit: int = 0, interval: float = 0.0, backoff: float = 0.0):
        """Initialize the sequence instance."""
        self.limit = limit
        self.interval = interval
        self.backoff = backoff

    def next_interval(self, index: int) -> float:
        """Calculate the time before the next attempt."""
        return pow(self.interval, 1 + (self.backoff * (index - 1)))

    def start(self) -> RepeatAttempt:
        """Get the first attempt in the sequence."""
        return RepeatAttempt(self)

    def __iter__(self):
        """Create a generator for the repeat attempts."""
        attempt = self.start()
        while True:
            yield attempt
            if attempt.final:
                break
            attempt = attempt.next()

    def __aiter__(self):
        """Implement async iterator protocol to wait between attempts."""
        return RepeatAttempt(self, index=0)

    def __repr__(self) -> str:
        """Format as a string for debugging."""
        return (
            f"<{self.__class__.__name__} "
            f"limit={self.limit} interval={self.interval} backoff={self.backoff}>"
        )
