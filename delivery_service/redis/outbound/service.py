"""Redis Outbound Delivery Service."""
import aiohttp
import aioredis
import argparse
import asyncio
import msgpack
import urllib
import sys

from time import time


def log_error(*args):
    """Print log error."""
    print(*args, file=sys.stderr)


class RedisHandler:
    """Redis outbound delivery."""

    def __init__(self, host: str, prefix: str):
        """Initialize RedisHandler."""
        self._host = host
        self._pool = None
        self.prefix = prefix
        self.retry_interval = 5
        self.retry_backoff = 0.25
        self.outbound_topic = f"{self.prefix}.outbound_transport"
        self.retry_topic = f"{self.prefix}.outbound_retry"

    async def run(self):
        """Run the service."""
        self._pool = await aioredis.create_pool(self._host)
        await asyncio.gather(self.process_delivery(), self.process_retries())

    async def process_delivery(self):
        """Process delivery of outbound messages."""
        http_client = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        async with self._pool.get() as conn:
            while True:
                (_, msg) = await conn.execute("BLPOP", self.outbound_topic, 0)
                msg = msgpack.unpackb(msg)
                if not isinstance(msg, dict):
                    log_error("Received non-dict message")
                elif b"endpoint" not in msg:
                    log_error("No endpoint provided")
                elif b"payload" not in msg:
                    log_error("No payload provided")
                else:
                    headers = {}
                    if b"headers" in msg:
                        for hname, hval in msg[b"headers"].items():
                            if isinstance(hval, bytes):
                                hval = hval.decode("utf-8")
                            headers[hname.decode("utf-8")] = hval
                    endpoint = msg[b"endpoint"].decode("utf-8")
                    payload = msg[b"payload"]
                    parsed = urllib.parse.urlparse(endpoint)
                    if parsed.scheme == "http" or parsed.scheme == "https":
                        print(f"Dispatch message to {endpoint}")
                        failed = False
                        try:
                            response = await http_client.post(
                                endpoint, data=payload, headers=headers, timeout=10
                            )
                        except aiohttp.ClientError as err:
                            log_error("Delivery error:", err)
                            failed = True
                        else:
                            if response.status < 200 or response.status >= 300:
                                log_error("Invalid response code:", response.status)
                                failed = True
                        if failed:
                            retries = msg.get(b"retries") or 0
                            if retries < 5:
                                await self.add_retry(
                                    {
                                        "endpoint": endpoint,
                                        "headers": headers,
                                        "payload": payload,
                                        "retries": retries + 1,
                                    }
                                )
                            else:
                                log_error("Exceeded max retries for", endpoint)
                    else:
                        log_error(f"Unsupported scheme: {parsed.scheme}")

    async def add_retry(self, message: dict):
        """Add undelivered message for future retries."""
        wait_interval = pow(
            self.retry_interval, 1 + (self.retry_backoff * (message["retries"] - 1))
        )
        retry_time = int(time() + wait_interval)
        await self._pool.execute(
            "ZADD", f"{self._topic}.outbound_retry", retry_time, msgpack.dumps(message)
        )

    async def process_retries(self):
        """Process retries."""
        async with self._pool.get() as conn:
            while True:
                max_score = int(time())
                rows = await conn.execute(
                    "ZRANGEBYSCORE",
                    self.retry_topic,
                    0,
                    max_score,
                    "LIMIT",
                    0,
                    10,
                )
                if rows:
                    for message in rows:
                        count = await conn.execute(
                            "ZREM",
                            self.retry_topic,
                            message,
                        )
                        if count == 0:
                            # message removed by another process
                            continue
                        await conn.execute("RPUSH", self.outbound_topic, message)
                else:
                    await asyncio.sleep(1)


async def main():
    """Start services."""
    parser = argparse.ArgumentParser(description="Redis Outbound Delivery Service.")
    parser.add_argument(
        "-oq",
        "--outbound-queue",
        dest="outbound_queue",
        type=str,
    )
    parser.add_argument(
        "-oqp",
        "--outbound-queue-prefix",
        dest="outbound_queue_prefix",
        type=str,
    )
    args = parser.parse_args()
    host = args.outbound_queue
    prefix = args.outbound_queue_prefix
    handler = RedisHandler(host, prefix)
    await handler.run()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
