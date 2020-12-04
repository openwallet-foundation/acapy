from tempfile import NamedTemporaryFile

from asynctest import TestCase as AsyncTestCase

from ...cache.base import BaseCache
from ...core.profile import ProfileManager
from ...core.protocol_registry import ProtocolRegistry
from ...transport.wire_format import BaseWireFormat

from ..default_context import DefaultContextBuilder
from ..injection_context import InjectionContext


class TestDefaultContext(AsyncTestCase):
    async def test_build_context(self):
        """Test context init."""

        builder = DefaultContextBuilder()
        result = await builder.build_context()
        assert isinstance(result, InjectionContext)

        for cls in (
            BaseCache,
            BaseWireFormat,
            ProfileManager,
            ProtocolRegistry,
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
