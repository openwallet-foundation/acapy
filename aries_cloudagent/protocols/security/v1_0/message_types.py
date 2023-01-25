"""Message type identifiers for Action Menus."""

from ...didcomm_prefix import DIDCommPrefix

# To be edited
TEST_SECURITY = "security/1.0/secure"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.security.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        # To be edited
        TEST_SECURITY: f"{PROTOCOL_PACKAGE}.secure.AddSecurity"
    }
)
