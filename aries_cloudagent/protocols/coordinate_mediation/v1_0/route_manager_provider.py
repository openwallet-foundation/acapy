"""RouteManager provider."""
from ....config.base import BaseInjector, BaseProvider, BaseSettings
from ....core.profile import Profile
from ....multitenant.base import BaseMultitenantManager
from ....multitenant.route_manager import MultitenantRouteManager
from .route_manager import CoordinateMediationV1RouteManager


class RouteManagerProvider(BaseProvider):
    """Route manager provider.

    Decides whcih route manager to use based on settings.
    """

    def __init__(self, root_profile: Profile):
        """Initialize route manager provider."""
        self.root_profile = root_profile

    def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create the appropriate route manager instance."""
        wallet_id = settings.get("wallet.id")
        multitenant_mgr = injector.inject_or(BaseMultitenantManager)
        profile = injector.inject(Profile)
        if multitenant_mgr and wallet_id:
            return MultitenantRouteManager(self.root_profile, profile, wallet_id)

        return CoordinateMediationV1RouteManager(profile)
