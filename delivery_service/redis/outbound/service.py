"""Redis Outbound Delivery Service."""
import aiohttp
import aioredis
import argparse
import asyncio
import logging
import msgpack
import urllib
import sys
import yaml

from time import time

logging.basicConfig(
    format="%(asctime)s | %(levelname)s: %(message)s",
    level=logging.INFO,
)


class RedisHandler:
    """Redis outbound delivery."""

    # for unit testing
    RUNNING = True
    RUNNING_RETRY = True

    def __init__(self, host: str, prefix: str):
        """Initialize RedisHandler."""
        self._host = host
        self.prefix = prefix
        self.retry_interval = 5
        self.retry_backoff = 0.25
        self.outbound_topic = f"{self.prefix}.outbound_transport"
        self.retry_topic = f"{self.prefix}.outbound_retry"
        self.redis = aioredis.from_url(self._host)
        self.retry_timedelay_s = 1

    async def run(self):
        """Run the service."""
        await asyncio.gather(self.process_delivery(), self.process_retries())

    async def process_delivery(self):
        """Process delivery of outbound messages."""
        http_client = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        try:
            while self.RUNNING:
                msg_received = False
                while not msg_received:
                    try:
                        msg = await self.redis.blpop(self.outbound_topic, 0)
                        msg_received = True
                    except aioredis.RedisError as err:
                        await asyncio.sleep(1)
                        logging.exception(
                            f"Unexpected redis client exception (blpop): {str(err)}"
                        )
                msg = msgpack.unpackb(msg[1])
                if not isinstance(msg, dict):
                    logging.error("Received non-dict message")
                elif b"endpoint" not in msg:
                    logging.error("No endpoint provided")
                elif b"payload" not in msg:
                    logging.error("No payload provided")
                else:
                    headers = {}
                    if b"headers" in msg:
                        for hname, hval in msg[b"headers"].items():
                            if isinstance(hval, bytes):
                                hval = hval.decode("utf-8")
                            headers[hname.decode("utf-8")] = hval
                    endpoint = msg[b"endpoint"].decode("utf-8")
                    payload = msg[b"payload"].decode("utf-8")
                    parsed = urllib.parse.urlparse(endpoint)
                    if parsed.scheme == "http" or parsed.scheme == "https":
                        logging.info(f"Dispatch message to {endpoint}")
                        failed = False
                        try:
                            response = await http_client.post(
                                endpoint, data=payload, headers=headers, timeout=10
                            )
                        except aiohttp.ClientError:
                            failed = True
                        except asyncio.TimeoutError:
                            failed = True
                        else:
                            if response.status < 200 or response.status >= 300:
                                logging.error("Invalid response code:", response.status)
                                failed = True
                        if failed:
                            logging.exception(f"Delivery failed for {endpoint}")
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
                                logging.error(
                                    f"Exceeded max retries for {str(endpoint)}"
                                )
                    else:
                        logging.error(f"Unsupported scheme: {parsed.scheme}")
        finally:
            await http_client.close()

    async def add_retry(self, message: dict):
        """Add undelivered message for future retries."""
        zadd_sent = False
        while not zadd_sent:
            try:
                wait_interval = pow(
                    self.retry_interval,
                    1 + (self.retry_backoff * (message["retries"] - 1)),
                )
                retry_time = int(time() + wait_interval)
                await self.redis.zadd(
                    f"{self.prefix}.outbound_retry",
                    {msgpack.packb(message): retry_time},
                )
                zadd_sent = True
            except aioredis.RedisError as err:
                await asyncio.sleep(1)
                logging.exception(
                    f"Unexpected redis client exception (zadd): {str(err)}"
                )

    async def process_retries(self):
        """Process retries."""
        while self.RUNNING_RETRY:
            zrangebyscore_rec = False
            while not zrangebyscore_rec:
                max_score = int(time())
                try:
                    rows = await self.redis.zrangebyscore(
                        name=self.retry_topic,
                        min=0,
                        max=max_score,
                        start=0,
                        num=10,
                    )
                    zrangebyscore_rec = True
                except aioredis.RedisError as err:
                    await asyncio.sleep(1)
                    logging.exception(
                        f"Unexpected redis client exception (zrangebyscore): {str(err)}"
                    )
            if rows:
                for message in rows:
                    zrem_rec = False
                    while not zrem_rec:
                        try:
                            count = await self.redis.zrem(
                                self.retry_topic,
                                message,
                            )
                            zrem_rec = True
                        except aioredis.RedisError as err:
                            await asyncio.sleep(1)
                            logging.exception(
                                f"Unexpected redis client exception (zrem): {str(err)}"
                            )
                    if count == 0:
                        # message removed by another process
                        continue
                    msg_sent = False
                    while not msg_sent:
                        try:
                            await self.redis.rpush(self.outbound_topic, message)
                            msg_sent = True
                        except aioredis.RedisError as err:
                            await asyncio.sleep(1)
                            logging.exception(
                                f"Unexpected redis client exception (rpush): {str(err)}"
                            )
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
