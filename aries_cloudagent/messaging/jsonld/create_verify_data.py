"""
Contains the functions needed to produce and verify a json-ld signature.

This file was ported from
https://github.com/transmute-industries/Ed25519Signature2018/blob/master/src/createVerifyData/index.js
"""

import datetime
import hashlib

from pyld import jsonld

from ...core.error import BaseError


def _canonize(data):
    return jsonld.normalize(
        data, {"algorithm": "URDNA2015", "format": "application/n-quads"}
    )


def _sha256(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _cannonize_signature_options(signatureOptions):
    _signatureOptions = {**signatureOptions, "@context": "https://w3id.org/security/v2"}
    _signatureOptions.pop("jws", None)
    _signatureOptions.pop("signatureValue", None)
    _signatureOptions.pop("proofValue", None)
    return _canonize(_signatureOptions)


def _cannonize_document(doc):
    _doc = {**doc}
    _doc.pop("proof", None)
    return _canonize(_doc)


class JsonldError(BaseError):
    """JsonLD validate or sign Error."""


class DroppedAttributeException(JsonldError):
    """Exception used to track that an attribute was removed."""


class VerificationMethodMissing(JsonldError):
    """VerificationMethod is required."""


class SignatureTypeError(JsonldError):
    """Signature type error."""


def create_verify_data(data, signature_options):
    """Encapsulate the process of constructing the string used during sign and verify."""

    signature_options["type"] = "Ed25519Signature2018"
    if "creator" in signature_options:
        signature_options["verificationMethod"] = signature_options["creator"]

    if not signature_options["verificationMethod"]:
        raise VerificationMethodMissing(
            "signature_options.verificationMethod is required"
        )

    def created_at():
        stamp = datetime.datetime.now(datetime.timezone.utc)
        return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")

    signature_options["created"] = signature_options.get("created", created_at())

    # TODO: povide methods for jsonld expand that reports dropped attributes for better error reporting
    [expanded] = jsonld.expand(data, {"keepFreeFloatingNodes": True})
    framed = jsonld.compact(
        expanded, "https://w3id.org/security/v2", {"skipExpansion": True}
    )
    # Detect any dropped attributes during the expand/contract step.
    if len(data) > len(framed):
        # attempt to collect error report data
        for_diff = jsonld.compact(expanded, data.get("@context"))
        dropped = set(data.keys()) - set(for_diff.keys())
        raise DroppedAttributeException(
            f"{dropped} attributes dropped. "
            " Provide definitions in context to correct."
        )
    # Check proof for dropped attributes
    attr = [
        ("proof", "proof"),
        ("credentialSubject", "https://www.w3.org/2018/credentials#credentialSubject"),
    ]
    data_context = data.get("@context")
    for maping in attr:
        data_attribute = data.get(maping[0], {})
        frame_attribute = framed.get(maping[1], {})
        if len(data_attribute) > len(frame_attribute):
            for_diff = jsonld.compact(expanded, data_context)
            for_diff_attribute = for_diff.get(maping[1], {})
            dropped = set(data_attribute.keys()) - set(for_diff_attribute.keys())
            raise DroppedAttributeException(
                f"in {maping[0]}, {dropped} attributes dropped."
                "Provide definitions in context to correct."
            )

    cannonized_signature_options = _cannonize_signature_options(signature_options)
    hash_of_cannonized_signature_options = _sha256(cannonized_signature_options)
    cannonized_document = _cannonize_document(framed)
    hash_of_cannonized_document = _sha256(cannonized_document)

    return (framed, hash_of_cannonized_signature_options + hash_of_cannonized_document)
