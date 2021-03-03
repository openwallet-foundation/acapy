import asyncio
import base64
import msgpack
import pytest
import string

from asynctest import TestCase as AsyncTestCase, mock as async_mock
import unittest
from aiohttp import web
import aioredis

from .....config.injection_context import InjectionContext
from .....utils.stats import Collector

from ....outbound.message import OutboundMessage
from ....wire_format import JsonWireFormat

from ...base import OutboundTransportError
from ..base import OutboundQueueError
from ..loader import (
    get_outbound_queue,
    get_class,
    get_connection_parts,
    OutboundQueueConfigurationError,
)
from ..redis import RedisOutboundQueue

from .fixtures import QueueClassValid


class TestQueueLoader(AsyncTestCase):
    async def test_get_class(self):
        with self.assertRaises(OutboundQueueConfigurationError) as context:
            get_class(
                "aries_cloudagent.transport.outbound.queue.tests.fixtures:"
                "QueueClassNoBaseClass"
            )
        self.assertIn("does not inherit", context.exception.message)
        with self.assertRaises(OutboundQueueConfigurationError) as context:
            get_class(
                "aries_cloudagent.transport.outbound.queue.tests.fixtures:"
                "NoClassThere"
            )
        self.assertIn("not found", context.exception.message)
        with self.assertRaises(OutboundQueueConfigurationError) as context:
            get_class(
                "aries_cloudagent.transport.outbound.queue.tests.fixtures:"
                "QueueClassNoProtocol"
            )
        self.assertIn("requires a defined 'protocol'", context.exception.message)
        self.assertIs(
            get_class(
                "aries_cloudagent.transport.outbound.queue.tests.fixtures:"
                "QueueClassValid"
            ),
            QueueClassValid,
        )

    async def test_get_connection_parts(self):
        protocol, host, port = get_connection_parts("redis://127.0.0.1:8000")
        self.assertEqual(protocol, "redis")
        self.assertEqual(host, "127.0.0.1")
        self.assertEqual(port, "8000")

    async def test_get_outbound_queue_valid(self):
        context = InjectionContext()
        context.settings["transport.outbound_queue"] = "testprotocol://127.0.0.1:8000"
        context.settings["transport.outbound_queue_prefix"] = "test_prefix"
        context.settings["transport.outbound_queue_class"] = (
            "aries_cloudagent.transport.outbound.queue.tests.fixtures:"
            "QueueClassValid"
        )
        queue = get_outbound_queue(context.settings)
        self.assertIsInstance(
            queue,
            QueueClassValid,
        )
        self.assertEqual(queue.connection, "testprotocol://127.0.0.1:8000")
