"""Redis Outbound Delivery Service."""
import aiohttp
import asyncio
import logging
import msgpack
import sys
import urllib
import uvicorn

from configargparse import ArgumentParser
from fastapi import Security, Depends, APIRouter, HTTPException
from fastapi.security.api_key import APIKeyHeader
from redis.cluster import RedisCluster as Redis
from redis.exceptions import RedisError
from time import time

logging.basicConfig(
    format="%(asctime)s | %(levelname)s: %(message)s",
    level=logging.INFO,
)


class RedisHandler:
    """Redis outbound delivery."""

    running = False
    ready = False

    def __init__(self, host: str, prefix: str):
        """Initialize RedisHandler."""
        self._host = host
        self.prefix = prefix
        self.retry_interval = 5
        self.retry_backoff = 0.25
        self.outbound_topic = f"{self.prefix}.outbound_transport"
        self.retry_topic = f"{self.prefix}.outbound_retry"
        self.redis = Redis.from_url(self._host)
        self.retry_timedelay_s = 1

    async def run(self):
        """Run the service."""
        try:
            self.redis.ping()
            self.ready = True
            self.running = True
            await asyncio.gather(self.process_delivery(), self.process_retries())
        except RedisError:
            self.ready = False
            self.running = False

    def is_running(self) -> bool:
        """Check if delivery service agent is running properly."""
        try:
            self.redis.ping()
            if self.running:
                return True
            else:
                return False
        except RedisError:
            return False

    async def process_delivery(self):
        """Process delivery of outbound messages."""
        http_client = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        try:
            while self.running:
                msg_received = False
                while not msg_received:
                    try:
                        msg = self.redis.blpop(self.outbound_topic, 0.2)
                        msg_received = True
                    except RedisError as err:
                        await asyncio.sleep(1)
                        logging.exception(
                            f"Unexpected redis client exception (blpop): {str(err)}"
                        )
                if not msg:
                    await asyncio.sleep(1)
                    continue
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
                self.redis.zadd(
                    f"{self.prefix}.outbound_retry",
                    {msgpack.packb(message): retry_time},
                )
                zadd_sent = True
            except RedisError as err:
                await asyncio.sleep(1)
                logging.exception(
                    f"Unexpected redis client exception (zadd): {str(err)}"
                )

    async def process_retries(self):
        """Process retries."""
        while self.running:
            zrangebyscore_rec = False
            while not zrangebyscore_rec:
                max_score = int(time())
                try:
                    rows = self.redis.zrangebyscore(
                        name=self.retry_topic,
                        min=0,
                        max=max_score,
                        start=0,
                        num=10,
                    )
                    zrangebyscore_rec = True
                except RedisError as err:
                    await asyncio.sleep(1)
                    logging.exception(
                        f"Unexpected redis client exception (zrangebyscore): {str(err)}"
                    )
            if rows:
                for message in rows:
                    zrem_rec = False
                    while not zrem_rec:
                        try:
                            count = self.redis.zrem(
                                self.retry_topic,
                                message,
                            )
                            zrem_rec = True
                        except RedisError as err:
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
                            self.redis.rpush(self.outbound_topic, message)
                            msg_sent = True
                        except RedisError as err:
                            await asyncio.sleep(1)
                            logging.exception(
                                f"Unexpected redis client exception (rpush): {str(err)}"
                            )
            else:
                await asyncio.sleep(self.retry_timedelay_s)


router = APIRouter()
API_KEY_NAME = "access_token"
X_API_KEY = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(x_api_key: str = Security(X_API_KEY)):
    """Extract and authenticate Header API_KEY."""
    if x_api_key == API_KEY:
        return x_api_key
    else:
        raise HTTPException(status_code=403, detail="Could not validate key")


async def start_handler(host, prefix):
    """Start Redis Handler."""
    global handler
    handler = RedisHandler(host, prefix)
    logging.info(
        f"Starting Redis outbound delivery service agent with args: {host}, {prefix}"
    )
    await handler.run()


@router.get("/status/ready")
def status_ready(api_key: str = Depends(get_api_key)):
    """Request handler for readiness check."""
    return {"ready": handler.ready}


@router.get("/status/live")
def status_live(api_key: str = Depends(get_api_key)):
    """Request handler for liveliness check."""
    return {"alive": handler.is_running()}


def main(args):
    """Start services."""
    args = argument_parser(args)
    if args.outbound_queue:
        host = args.outbound_queue
    else:
        raise SystemExit("No Redis host/connection provided.")
    if args.outbound_queue_prefix:
        prefix = args.outbound_queue_prefix
    else:
        prefix = "acapy"
    if args.endpoint_transport:
        delivery_Service_endpoint_transport = args.endpoint_transport
    else:
        raise SystemExit("No Delivery Service api config provided.")
    if args.endpoint_api_key:
        delivery_Service_api_key = args.endpoint_api_key
    else:
        raise SystemExit("No Delivery Service api key provided.")
    global API_KEY
    API_KEY = delivery_Service_api_key
    api_host, api_port = delivery_Service_endpoint_transport
    asyncio.ensure_future(start_handler(host, prefix))
    logging.info(f"Starting FastAPI service: http://{api_host}:{api_port}")
    uvicorn.run(router, host=api_host, port=int(api_port))


def argument_parser(args):
    """Argument parser."""
    parser = ArgumentParser(description="Redis Outbound Delivery Service.")
    parser.add_argument(
        "-oq",
        "--outbound-queue",
        dest="outbound_queue",
        type=str,
        env_var="ACAPY_OUTBOUND_TRANSPORT_QUEUE",
    )
    parser.add_argument(
        "-oqp",
        "--outbound-queue-prefix",
        dest="outbound_queue_prefix",
        type=str,
        default="acapy",
        env_var="ACAPY_OUTBOUND_TRANSPORT_QUEUE_PREFIX",
    )
    parser.add_argument(
        "--endpoint-transport",
        dest="endpoint_transport",
        type=str,
        required=False,
        nargs=2,
        metavar=("<host>", "<port>"),
        env_var="DELIVERY_SERVICE_ENDPOINT_TRANSPORT",
    )
    parser.add_argument(
        "--endpoint-api-key",
        dest="endpoint_api_key",
        type=str,
        env_var="DELIVERY_SERVICE_ENDPOINT_KEY",
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    main(sys.argv[1:])
