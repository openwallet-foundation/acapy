"""Message type identifiers for Issuer Registrations."""

MESSAGE_FAMILY = "did:sov:NewAUq29E4jLJ5jMSxns3s;spec/issuer-registration/1.0"

REGISTER = f"{MESSAGE_FAMILY}/register"

MESSAGE_TYPES = {
    REGISTER: "indy_catalyst_issuer_registration."
    + "messages.register.IssuerRegistration"
}
