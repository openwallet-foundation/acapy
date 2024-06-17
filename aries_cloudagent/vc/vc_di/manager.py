"""Manager for managing DIF DataIntegrityProof presentations over JSON-LD formatted W3C VCs."""

from typing import Dict, List, Optional, Type, Union, cast

from pyld import jsonld
from pyld.jsonld import JsonLdProcessor

from ...core.profile import Profile
from ..vc_ld.models.presentation import VerifiablePresentation
from ..vc_ld.validation_result import PresentationVerificationResult
from ..vc_ld.models.options import LDProofVCOptions
from .verify import verify_signed_anoncredspresentation


class VcDiManagerError(Exception):
    """Generic VcLdpManager Error."""


class VcDiManager:
    """Class for managing DIF DataIntegrityProof presentations over JSON-LD formatted W3C VCs."""

    def __init__(self, profile: Profile):
        """Initialize the VC DI Proof Manager."""
        self.profile = profile

    async def verify_presentation(
        self, vp: VerifiablePresentation, options: dict
    ) -> PresentationVerificationResult:
        """Verify a VP with a Linked Data Proof."""

        if not options["options"]["challenge"]:
            raise VcDiManagerError("Challenge is required for verifying a VP")

        return await verify_signed_anoncredspresentation(
            profile=self.profile,
            presentation=vp.serialize(),
            challenge=options["options"]["challenge"],
            pres_req=options,
        )
