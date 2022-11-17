"""Classes representing inbound messages."""

import asyncio
from typing import Union

from .receipt import MessageReceipt


class InboundMessage:
    """Container class linking a message payload with its receipt details."""

    def __init__(
        self,
        payload: Union[str, bytes],
        receipt: MessageReceipt,
        *,
        connection_id: str = None,
        session_id: str = None,
        transport_type: str = None,
    ):
        """Initialize the inbound message."""
        self.connection_id = connection_id
        self.payload = payload
        self.receipt = receipt
        self.session_id = session_id
        self.transport_type = transport_type
        self.processing_complete_event = asyncio.Event()

    def dispatch_processing_complete(self):
        """Dispatch processing complete."""
        self.processing_complete_event.set()

    async def wait_processing_complete(self):
        """Wait for processing to complete."""
        await self.processing_complete_event.wait()
