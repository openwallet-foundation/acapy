from ....vc.tests.contexts import (
    CITIZENSHIP_V1,
    CREDENTIALS_V1,
    EXAMPLES_V1,
    ODRL,
    SCHEMA_ORG,
    SECURITY_V1,
    SECURITY_V2,
)

from . import (
    TEST_EURO_HEALTH,
    TEST_SIGN_OBJ0,
    TEST_SIGN_OBJ1,
    TEST_SIGN_OBJ2,
    TEST_VALIDATE_ERROR_OBJ2,
    TEST_VERIFY_ERROR,
    TEST_VERIFY_OBJ0,
    TEST_VERIFY_OBJ1,
    TEST_VERIFY_OBJ2,
)

DOCUMENTS = {
    TEST_SIGN_OBJ0["doc"]["id"]: TEST_SIGN_OBJ0["doc"],
    TEST_SIGN_OBJ1["doc"]["id"]: TEST_SIGN_OBJ1["doc"],
    TEST_VERIFY_ERROR["doc"]["id"]: TEST_VERIFY_ERROR["doc"],
    TEST_VERIFY_OBJ0["doc"]["id"]: TEST_VERIFY_OBJ0["doc"],
    TEST_VERIFY_OBJ1["doc"]["id"]: TEST_VERIFY_OBJ1["doc"],
    "https://w3id.org/citizenship/v1": CITIZENSHIP_V1,
    "https://www.w3.org/2018/credentials/v1": CREDENTIALS_V1,
    "https://www.w3.org/2018/credentials/examples/v1": EXAMPLES_V1,
    "https://www.w3.org/ns/odrl.jsonld": ODRL,
    "http://schema.org/": SCHEMA_ORG,
    "https://w3id.org/security/v1": SECURITY_V1,
    "https://w3id.org/security/v2": SECURITY_V2,
    (
        "https://essif-lab.pages.grnet.gr/interoperability/"
        "eidas-generic-use-case/contexts/ehic-v1.jsonld"
    ): TEST_EURO_HEALTH,
}


def custom_document_loader(url: str, options: dict):
    # Check if full url (with fragments is in document map)
    if url in DOCUMENTS:
        return {
            "contentType": "application/ld+json",
            "contextUrl": None,
            "document": DOCUMENTS[url],
            "documentUrl": url,
        }

    # Otherwise look if it is present without fragment
    without_fragment = url.split("#")[0]
    if without_fragment in DOCUMENTS:
        return {
            "contentType": "application/ld+json",
            "contextUrl": None,
            "document": DOCUMENTS[without_fragment],
            "documentUrl": url,
        }

    raise Exception(f"No custom context support for {url}")
