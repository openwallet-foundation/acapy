from ..config.provider import BaseProvider
from ..config.settings import BaseSettings
from ..config.injector import BaseInjector
from .manager import MultitenantManager
from .askar_profile_manager import AskarProfileMultitenantManager

class MultitenantManagerProvider(BaseProvider):
    """The standard multitenant profile manager provider decides which manager to use based on the settings"""

    def __init__(self, root_profile):
        """Initialize the multitenant profile manager provider."""
        self.root_profile = root_profile

    def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create the profile manager instance."""

        if settings.get("multitenant.type") == "askar":
            return  AskarProfileMultitenantManager(self.root_profile)
        return MultitenantManager(self.root_profile)
