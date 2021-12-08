import asyncio
import urllib
import sys

from time import time

import aiohttp
import aioredis
import msgpack


def log_error(*args):
    print(*args, file=sys.stderr)


class RedisHandler:
    def __init__(self, host: str, topic: str):
        self._host = host
        self._pool = None
        self._topic = topic
        self.retry_interval = 5
        self.retry_backoff = 0.25

    async def run(self):
        self._pool = await aioredis.create_pool(self._host)
        await asyncio.gather(self.process_delivery(), self.process_retries())

    async def process_delivery(self):
        http_client = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        print("Listening for messages..")
        topic = f"{self._topic}.outbound_transport"
        async with self._pool.get() as conn:
            while True:
                (_, msg) = await conn.execute("BLPOP", topic, 0)
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
        wait_interval = pow(
            self.retry_interval, 1 + (self.retry_backoff * (message["retries"] - 1))
        )
        retry_time = int(time() + wait_interval)
        await self._pool.execute(
            "ZADD", f"{self._topic}.outbound_retry", retry_time, msgpack.dumps(message)
        )

    async def process_retries(self):
        outbound_topic = f"{self._topic}.outbound_transport"
        retry_topic = f"{self._topic}.outbound_retry"
        async with self._pool.get() as conn:
            while True:
                max_score = int(time())
                rows = await conn.execute(
                    "ZRANGEBYSCORE",
                    retry_topic,
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
                            retry_topic,
                            message,
                        )
                        if count == 0:
                            # message removed by another process
                            continue
                        await conn.execute("RPUSH", outbound_topic, message)
                else:
                    await asyncio.sleep(1)


async def main(host: str, topic: str):
    handler = RedisHandler(host, topic)
    await handler.run()


if __name__ == "__main__":
    args = sys.argv
    if len(args) <= 1:
        raise SystemExit("Pass redis host URL as the first parameter")
    if len(args) > 2:
        topic = args[2]
    else:
        topic = "acapy"

    asyncio.get_event_loop().run_until_complete(main(args[1], topic))