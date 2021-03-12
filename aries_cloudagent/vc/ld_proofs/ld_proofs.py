from typing import Union

from .ProofSet import ProofSet
from .suites import LinkedDataSignature
from .document_loader import DocumentLoader
from .purposes import ProofPurpose
from pyld.jsonld import JsonLdError
from .VerificationException import VerificationException


async def sign(
    *,
    document: dict,
    suite: LinkedDataSignature,
    purpose: ProofPurpose,
    document_loader: DocumentLoader,
):
    try:
        return await ProofSet().add(
            document=document,
            suite=suite,
            purpose=purpose,
            document_loader=document_loader,
        )

    except JsonLdError as e:
        if e.type == "jsonld.InvalidUrl":
            raise Exception(
                f'A URL "{e.details}" could not be fetched; you need to pass a DocumentLoader function that can resolve this URL, or resolve the URL before calling "sign".'
            )
    except Exception as e:
        raise e


async def verify(
    *,
    document: Union[dict, str],
    suites: LinkedDataSignature,
    purpose: ProofPurpose,
    document_loader: DocumentLoader,
):
    result = await ProofSet().verify(
        document=document,
        suites=suites,
        purpose=purpose,
        document_loader=document_loader,
    )

    if result["error"]:
        if (
            hasattr(result["error"], "type")
            and result["error"].type == "jsonld.InvalidUrl"
        ):
            url_err = Exception(
                f'A URL "{result["error"].details}" could not be fetched; you need to pass a DocumentLoader function that can resolve this URL, or resolve the URL before calling "sign".'
            )
            result["error"] = VerificationException(url_err)
    else:
        result["error"] = VerificationException(result["error"])

    return result
