"""
Contains the functions needed to produce and verify a json-ld signature.

This file was ported from
https://github.com/transmute-industries/Ed25519Signature2018/blob/master/
    src/createVerifyData/index.js
"""

import datetime
import hashlib

from pyld import jsonld

from .error import DroppedAttributeError, MissingVerificationMethodError


def _canonize(data):
    return jsonld.normalize(
        data, {"algorithm": "URDNA2015", "format": "application/n-quads"}
    )


def _sha256(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _canonize_signature_options(signatureOptions):
    _signatureOptions = {**signatureOptions, "@context": "https://w3id.org/security/v2"}
    _signatureOptions.pop("jws", None)
    _signatureOptions.pop("signatureValue", None)
    _signatureOptions.pop("proofValue", None)
    return _canonize(_signatureOptions)


def _canonize_document(doc):
    _doc = {**doc}
    _doc.pop("proof", None)
    return _canonize(_doc)


def create_verify_data(data, signature_options):
    """Encapsulate the process of constructing the string used during sign and verify."""

    if "creator" in signature_options:
        signature_options["verificationMethod"] = signature_options["creator"]

    if not signature_options.get("verificationMethod"):
        raise MissingVerificationMethodError(
            "signature_options.verificationMethod is required"
        )

    if "created" not in signature_options:
        signature_options["created"] = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

    if (
        "type" not in signature_options
        or signature_options["type"] != "Ed25519Signature2018"
    ):
        signature_options["type"] = "Ed25519Signature2018"

    [expanded] = jsonld.expand(data)
    framed = jsonld.compact(
        expanded, "https://w3id.org/security/v2", {"skipExpansion": True}
    )

    # Detect any dropped attributes during the expand/contract step.
    if len(data) != len(framed):
        raise DroppedAttributeError("Extra Attribute Detected")
    if (
        "proof" in data
        and "proof" in framed
        and len(data["proof"]) != len(framed["proof"])
    ):
        raise DroppedAttributeError("Extra Attribute Detected")
    if (
        "credentialSubject" in data
        and "https://www.w3.org/2018/credentials#credentialSubject" in framed
        and len(data["credentialSubject"])
        != len(framed["https://www.w3.org/2018/credentials#credentialSubject"])
    ):
        raise DroppedAttributeError("Extra Attribute Detected")

    canonized_signature_options = _canonize_signature_options(signature_options)
    hash_of_canonized_signature_options = _sha256(canonized_signature_options)
    canonized_document = _canonize_document(framed)
    hash_of_canonized_document = _sha256(canonized_document)

    return (framed, hash_of_canonized_signature_options + hash_of_canonized_document)
