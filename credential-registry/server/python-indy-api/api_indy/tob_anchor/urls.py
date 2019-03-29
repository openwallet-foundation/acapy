from aiohttp.web import RouteDef
from . import views

def get_routes():
    return [RouteDef(*args) for args in (
        ("POST", "/api/v2/indy/construct-proof", views.construct_proof, {}),
        ("POST", "/api/v2/indy/generate-credential-request", views.generate_credential_request, {}),
        ("POST", "/api/v2/indy/store-credential", views.store_credential, {}),
        ("POST", "/api/v2/indy/register-issuer", views.register_issuer, {}),
        #("GET", "/api/v2/indy/debug", views.request_info, {}),  # Do not expose in PROD
        ("GET", "/health", views.combined_health, {}), # Replaces tob_api health endpoint
        #("GET", "/api/v2/indy/health", views.health, {}),
        ("GET", "/api/v2/indy/status", views.status, {}),
        ("GET", "/api/v2/credential/{id}/verify", views.verify_credential, {}),
    )]
