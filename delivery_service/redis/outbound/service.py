"""Redis Outbound Delivery Service."""
import aiohttp
import aioredis
import argparse
import asyncio
import msgpack
import urllib
import sys
import yaml

from time import time


def log_error(*args):
    """Print log error."""
    print(*args, file=sys.stderr)


class RedisHandler:
    """Redis outbound delivery."""

    # for unit testing
    RUNNING = True
    RUNNING_RETRY = True

    def __init__(self, host: str, prefix: str):
        """Initialize RedisHandler."""
        self._host = host
        self._pool = None
        self.prefix = prefix
        self.retry_interval = 5
        self.retry_backoff = 0.25
        self.outbound_topic = f"{self.prefix}.outbound_transport"
        self.retry_topic = f"{self.prefix}.outbound_retry"
        self.pool = aioredis.ConnectionPool.from_url(self._host, max_connections=10)
        self.redis = aioredis.Redis(connection_pool=self.pool)
        self.retry_timedelay_s = 1

    async def run(self):
        """Run the service."""
        await asyncio.gather(self.process_delivery(), self.process_retries())

    async def process_delivery(self):
        """Process delivery of outbound messages."""
        http_client = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        try:
            while self.RUNNING:
                msg = await self.redis.blpop(self.outbound_topic, 0)
                msg = msgpack.unpackb(msg)
                if not isinstance(msg, dict):
                    log_error("Received non-dict message")
                elif "endpoint" not in msg:
                    log_error("No endpoint provided")
                elif "payload" not in msg:
                    log_error("No payload provided")
                else:
                    headers = {}
                    if "headers" in msg:
                        for hname, hval in msg["headers"].items():
                            if isinstance(hval, bytes):
                                hval = hval.decode("utf-8")
                            headers[hname] = hval
                    endpoint = msg["endpoint"]
                    payload = msg["payload"]
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
                            retries = msg.get("retries") or 0
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
        finally:
            await http_client.close()

    async def add_retry(self, message: dict):
        """Add undelivered message for future retries."""
        wait_interval = pow(
            self.retry_interval, 1 + (self.retry_backoff * (message["retries"] - 1))
        )
        retry_time = int(time() + wait_interval)
        await self.redis.zadd(
            f"{self.prefix}.outbound_retry", retry_time, msgpack.dumps(message)
        )

    async def process_retries(self):
        """Process retries."""
        while self.RUNNING_RETRY:
            max_score = int(time())
            rows = await self.redis.zrangebyscore(
                self.retry_topic,
                0,
                max_score,
                "LIMIT",
                0,
                10,
            )
            if rows:
                for message in rows:
                    count = await self.redis.zrem(
                        self.retry_topic,
                        message,
                    )
                    if count == 0:
                        # message removed by another process
                        continue
                    await self.redis.rpush(self.outbound_topic, message)
            else:
                await asyncio.sleep(self.retry_timedelay_s)


async def main(args):
    """Start services."""
    args = argument_parser(args)
    config = None
    if args.plugin_config:
        with open(args.plugin_config, "r") as stream:
            loaded_plugin_config = yaml.safe_load(stream)
        config = loaded_plugin_config.get("redis_outbound_queue")
    if args.outbound_queue:
        host = args.outbound_queue
    elif config:
        host = config["connection"]
    else:
        raise SystemExit("No Redis host/connection provided.")
    if config:
        prefix = config.get("prefix", "acapy")
    elif args.outbound_queue_prefix:
        prefix = args.outbound_queue_prefix
    handler = RedisHandler(host, prefix)
    await handler.run()


def argument_parser(args):
    """Argument parser."""
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
        default="acapy",
    )
    parser.add_argument(
        "--plugin-config",
        dest="plugin_config",
        type=str,
        required=False,
        help="Load YAML file path that defines external plugin configuration.",
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main(sys.argv[1:]))
