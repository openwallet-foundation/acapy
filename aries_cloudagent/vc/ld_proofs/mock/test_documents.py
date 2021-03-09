from ..constants import SECURITY_CONTEXT_V2_URL

non_security_context_test_doc = {
    "@context": {
        "schema": "http://schema.org/",
        "name": "schema:name",
        "homepage": "schema:url",
        "image": "schema:image",
    },
    "name": "Manu Sporny",
    "homepage": "https://manu.sporny.org/",
    "image": "https://manu.sporny.org/images/manu.png",
}

security_context_test_doc = {
    **non_security_context_test_doc,
    "@context": [
        {"@version": 1.1},
        non_security_context_test_doc["@context"],
        SECURITY_CONTEXT_V2_URL,
    ],
}
