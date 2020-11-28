from tempfile import NamedTemporaryFile

from asynctest import TestCase as AsyncTestCase

from ...core.protocol_registry import ProtocolRegistry
from ...storage.base import BaseStorage
from ...transport.wire_format import BaseWireFormat
from ...wallet.base import BaseWallet

from ..default_context import DefaultContextBuilder
from ..injection_context import InjectionContext


class TestDefaultContext(AsyncTestCase):
    async def test_build_context(self):
        """Test context init."""

        builder = DefaultContextBuilder()
        result = await builder.build_context()
        assert isinstance(result, InjectionContext)

        for cls in (
            BaseWireFormat,
            ProtocolRegistry,
            BaseWallet,
            BaseStorage,
        ):
            assert isinstance(result.inject(cls), cls)

        builder = DefaultContextBuilder(
            settings={
                "timing.enabled": True,
                "timing.log.file": NamedTemporaryFile().name,
            }
        )
        result = await builder.build_context()
        assert isinstance(result, InjectionContext)
