from ..config.injection_context import InjectionContext
from ..config.provider import ClassProvider
from ..core.profile import Profile


async def setup(context: InjectionContext):
    """Setup vc plugin."""
    from .vc_ld.manager import VcLdpManager

    context.injector.bind_provider(
        VcLdpManager, ClassProvider(VcLdpManager, ClassProvider.Inject(Profile))
    )
