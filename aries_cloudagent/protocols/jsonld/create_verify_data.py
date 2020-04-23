#ported from https://github.com/transmute-industries/Ed25519Signature2018/blob/master/src/createVerifyData/index.js
import datetime

from pyld import jsonld
import hashlib


def _canonize(data):
    return jsonld.canonicalize(data)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _cannonize_signature_options(signatureOptions):
    _signatureOptions = {
        **signatureOptions,
        "@context": "https://w3id.org/security/v2"
    }
    signatureOptions.pop('jws', None)
    signatureOptions.pop('signatureValue', None)
    signatureOptions.pop('proofValue', None)
    return _canonize(_signatureOptions)


def _cannonize_document(doc):
    _doc = { **doc }
    _doc.pop("proof", None)
    return _canonize(_doc)


def create_verify_data(data, signature_options):
    if 'creator' in signature_options:
        signature_options['verificationMethod'] = signature_options['creator']

    if not signature_options['verificationMethod']:
        raise Exception("signature_options.verificationMethod is required")

    if 'created' not in signature_options:
        signature_options['created'] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if 'type' not in signature_options or signature_options['type'] is not "Ed25519Signature2018":
        signature_options['type'] = "Ed25519Signature2018"

    [expanded] = jsonld.expand(data)
    framed = jsonld.compact(
        expanded,
        ["https://www.w3.org/2018/credentials/v1",
         "https://www.w3.org/2018/credentials/examples/v1"], #"https://w3id.org/security/v2"
        {"skipExpansion": True}
    )

    cannonized_signature_options = _cannonize_signature_options(
        signature_options
    )
    hash_of_cannonized_signature_options = _sha256(cannonized_signature_options)
    cannonized_document = _cannonize_document(framed)
    hash_of_cannonized_document = _sha256(cannonized_document)

    return (
        framed,
        hash_of_cannonized_signature_options + hash_of_cannonized_document
    )
