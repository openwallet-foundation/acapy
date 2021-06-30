"""
Utilities for dif presentation exchange attachment.

General Flow:
create_vp ->
make_requirement [create a Requirement from SubmissionRequirements and Descriptors] ->
apply_requirement [filter credentials] ->
merge [return applicable credential list and descriptor_map for presentation_submission]
returns VerifiablePresentation
"""
import pytz
import re

from datetime import datetime
from dateutil.parser import parse as dateutil_parser
from dateutil.parser import ParserError
from jsonpath_ng import parse
from pyld import jsonld
from pyld.jsonld import JsonLdProcessor
from typing import Sequence, Optional, Tuple
from unflatten import unflatten
from uuid import uuid4

from ....core.error import BaseError
from ....core.profile import Profile
from ....did.did_key import DIDKey
from ....storage.vc_holder.vc_record import VCRecord
from ....vc.ld_proofs import (
    Ed25519Signature2018,
    BbsBlsSignature2020,
    BbsBlsSignatureProof2020,
    WalletKeyPair,
    DocumentLoader,
)
from ....vc.ld_proofs.constants import (
    SECURITY_CONTEXT_BBS_URL,
    EXPANDED_TYPE_CREDENTIALS_CONTEXT_V1_VC_TYPE,
)
from ....vc.vc_ld.prove import sign_presentation, create_presentation, derive_credential
from ....wallet.base import BaseWallet, DIDInfo
from ....wallet.key_type import KeyType

from .pres_exch import (
    PresentationDefinition,
    InputDescriptors,
    DIFField,
    Filter,
    Constraints,
    SubmissionRequirements,
    Requirement,
    SchemaInputDescriptor,
    InputDescriptorMapping,
    PresentationSubmission,
)

PRESENTATION_SUBMISSION_JSONLD_CONTEXT = (
    "https://identity.foundation/presentation-exchange/submission/v1"
)
PRESENTATION_SUBMISSION_JSONLD_TYPE = "PresentationSubmission"


class DIFPresExchError(BaseError):
    """Base class for DIF Presentation Exchange related errors."""


class DIFPresExchHandler:
    """Base Presentation Exchange Handler."""

    ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING = {
        Ed25519Signature2018: KeyType.ED25519,
    }

    if BbsBlsSignature2020.BBS_SUPPORTED:
        ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING[BbsBlsSignature2020] = KeyType.BLS12381G2

    DERIVE_SIGNATURE_SUITE_KEY_TYPE_MAPPING = {
        BbsBlsSignatureProof2020: KeyType.BLS12381G2,
    }
    PROOF_TYPE_SIGNATURE_SUITE_MAPPING = {
        suite.signature_type: suite
        for suite, key_type in ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING.items()
    }
    DERIVED_PROOF_TYPE_SIGNATURE_SUITE_MAPPING = {
        suite.signature_type: suite
        for suite, key_type in DERIVE_SIGNATURE_SUITE_KEY_TYPE_MAPPING.items()
    }

    def __init__(
        self,
        profile: Profile,
        pres_signing_did: str = None,
        proof_type: str = None,
    ):
        """Initialize PresExchange Handler."""
        super().__init__()
        self.profile = profile
        self.pres_signing_did = pres_signing_did
        if not proof_type:
            self.proof_type = Ed25519Signature2018.signature_type
        else:
            self.proof_type = proof_type

    async def _get_issue_suite(
        self,
        *,
        wallet: BaseWallet,
        issuer_id: str,
    ):
        """Get signature suite for signing presentation."""
        did_info = await self._did_info_for_did(issuer_id)
        verification_method = self._get_verification_method(issuer_id)

        # Get signature class based on proof type
        SignatureClass = self.PROOF_TYPE_SIGNATURE_SUITE_MAPPING[self.proof_type]

        # Generically create signature class
        return SignatureClass(
            verification_method=verification_method,
            key_pair=WalletKeyPair(
                wallet=wallet,
                key_type=self.ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING[SignatureClass],
                public_key_base58=did_info.verkey if did_info else None,
            ),
        )

    async def _get_derive_suite(
        self,
        *,
        wallet: BaseWallet,
    ):
        """Get signature suite for deriving credentials."""
        # Get signature class based on proof type
        SignatureClass = self.DERIVED_PROOF_TYPE_SIGNATURE_SUITE_MAPPING[
            "BbsBlsSignatureProof2020"
        ]

        # Generically create signature class
        return SignatureClass(
            key_pair=WalletKeyPair(
                wallet=wallet,
                key_type=self.DERIVE_SIGNATURE_SUITE_KEY_TYPE_MAPPING[SignatureClass],
            ),
        )

    def _get_verification_method(self, did: str):
        """Get the verification method for a did."""
        if did.startswith("did:key:"):
            return DIDKey.from_did(did).key_id
        elif did.startswith("did:sov:"):
            # key-1 is what uniresolver uses for key id
            return did + "#key-1"
        else:
            raise DIFPresExchError(
                f"Unable to get retrieve verification method for did {did}"
            )

    async def _did_info_for_did(self, did: str) -> DIDInfo:
        """Get the did info for specified did.

        If the did starts with did:sov it will remove the prefix for
        backwards compatibility with not fully qualified did.

        Args:
            did (str): The did to retrieve from the wallet.

        Raises:
            WalletNotFoundError: If the did is not found in the wallet.

        Returns:
            DIDInfo: did information

        """
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)

            # If the did starts with did:sov we need to query without
            if did.startswith("did:sov:"):
                return await wallet.get_local_did(did.replace("did:sov:", ""))

            # All other methods we can just query
            return await wallet.get_local_did(did)

    async def get_sign_key_credential_subject_id(
        self, applicable_creds: Sequence[VCRecord]
    ) -> Tuple[Optional[str], Sequence[dict]]:
        """Get the issuer_id and filtered_creds from enclosed credentials subject_ids."""
        issuer_id = None
        filtered_creds_list = []
        if self.proof_type == BbsBlsSignature2020.signature_type:
            reqd_key_type = KeyType.BLS12381G2
        else:
            reqd_key_type = KeyType.ED25519
        for cred in applicable_creds:
            if len(cred.subject_ids) > 0:
                if not issuer_id:
                    for cred_subject_id in cred.subject_ids:
                        if not cred_subject_id.startswith("urn:"):
                            did_info = await self._did_info_for_did(cred_subject_id)
                            if did_info.key_type == reqd_key_type:
                                issuer_id = cred_subject_id
                                filtered_creds_list.append(cred.cred_value)
                                break
                else:
                    if issuer_id in cred.subject_ids:
                        filtered_creds_list.append(cred.cred_value)
                    else:
                        raise DIFPresExchError(
                            "Applicable credentials have different credentialSubject.id, "
                            "multiple proofs are not supported currently"
                        )
        return (issuer_id, filtered_creds_list)

    async def to_requirement(
        self, sr: SubmissionRequirements, descriptors: Sequence[InputDescriptors]
    ) -> Requirement:
        """
        Return Requirement.

        Args:
            sr: submission_requirement
            descriptors: list of input_descriptors
        Raises:
            DIFPresExchError: If not able to create requirement

        """
        input_descriptors = []
        nested = []
        total_count = 0

        if sr._from:
            if sr._from != "":
                for descriptor in descriptors:
                    if self.contains(descriptor.groups, sr._from):
                        input_descriptors.append(descriptor)
                total_count = len(input_descriptors)
                if total_count == 0:
                    raise DIFPresExchError(f"No descriptors for from: {sr._from}")
        else:
            for submission_requirement in sr.from_nested:
                try:
                    # recursion logic
                    requirement = await self.to_requirement(
                        submission_requirement, descriptors
                    )
                    nested.append(requirement)
                except Exception as err:
                    raise DIFPresExchError(
                        (
                            "Error creating requirement from "
                            f"nested submission_requirements, {err}"
                        )
                    )
            total_count = len(nested)
        count = sr.count
        if sr.rule == "all":
            count = total_count
        requirement = Requirement(
            count=count,
            maximum=sr.maximum,
            minimum=sr.minimum,
            input_descriptors=input_descriptors,
            nested_req=nested,
        )
        return requirement

    async def make_requirement(
        self,
        srs: Sequence[SubmissionRequirements] = None,
        descriptors: Sequence[InputDescriptors] = None,
    ) -> Requirement:
        """
        Return Requirement.

        Creates and return Requirement with nesting if required
        using to_requirement()

        Args:
            srs: list of submission_requirements
            descriptors: list of input_descriptors
        Raises:
            DIFPresExchError: If not able to create requirement

        """
        if not srs:
            srs = []
        if not descriptors:
            descriptors = []
        if len(srs) == 0:
            requirement = Requirement(
                count=len(descriptors),
                input_descriptors=descriptors,
            )
            return requirement
        requirement = Requirement(
            count=len(srs),
            nested_req=[],
        )
        for submission_requirement in srs:
            try:
                requirement.nested_req.append(
                    await self.to_requirement(submission_requirement, descriptors)
                )
            except Exception as err:
                raise DIFPresExchError(
                    f"Error creating requirement inside to_requirement function, {err}"
                )
        return requirement

    def is_len_applicable(self, req: Requirement, val: int) -> bool:
        """
        Check and validate requirement minimum, maximum and count.

        Args:
            req: Requirement
            val: int value to check
        Return:
            bool

        """
        if req.count:
            if req.count > 0 and val != req.count:
                return False
        if req.minimum:
            if req.minimum > 0 and req.minimum > val:
                return False
        if req.maximum:
            if req.maximum > 0 and req.maximum < val:
                return False
        return True

    def contains(self, data: Sequence[str], e: str) -> bool:
        """
        Check for e in data.

        Returns True if e exists in data else return False

        Args:
            data: Sequence of str
            e: str value to check
        Return:
            bool

        """
        data_list = list(data) if data else []
        for k in data_list:
            if e == k:
                return True
        return False

    async def filter_constraints(
        self,
        constraints: Constraints,
        credentials: Sequence[VCRecord],
    ) -> Sequence[VCRecord]:
        """
        Return list of applicable VCRecords after applying filtering.

        Args:
            constraints: Constraints
            credentials: Sequence of credentials
                to apply filtering on
        Return:
            Sequence of applicable VCRecords

        """
        document_loader = self.profile.inject(DocumentLoader)

        result = []
        for credential in credentials:
            if constraints.subject_issuer == "required" and not self.subject_is_issuer(
                credential=credential
            ):
                continue

            applicable = False
            for field in constraints._fields:
                applicable = await self.filter_by_field(field, credential)
                if applicable:
                    break
            if not applicable:
                continue

            if constraints.limit_disclosure == "required":
                credential_dict = credential.cred_value
                new_credential_dict = self.reveal_doc(
                    credential_dict=credential_dict, constraints=constraints
                )
                async with self.profile.session() as session:
                    wallet = session.inject(BaseWallet)
                    derive_suite = await self._get_derive_suite(
                        wallet=wallet,
                    )
                    signed_new_credential_dict = await derive_credential(
                        credential=credential_dict,
                        reveal_document=new_credential_dict,
                        suite=derive_suite,
                        document_loader=document_loader,
                    )
                    credential = self.create_vcrecord(signed_new_credential_dict)
            result.append(credential)
        return result

    def create_vcrecord(self, cred_dict: dict) -> VCRecord:
        """Return VCRecord from a credential dict."""
        proofs = cred_dict.get("proof") or []
        proof_types = None
        if type(proofs) is dict:
            proofs = [proofs]
        if proofs:
            proof_types = [proof.get("type") for proof in proofs]
        contexts = [ctx for ctx in cred_dict.get("@context") if type(ctx) is str]
        if "@graph" in cred_dict:
            for enclosed_data in cred_dict.get("@graph"):
                if (
                    enclosed_data["id"].startswith("urn:")
                    and "credentialSubject" in enclosed_data
                ):
                    cred_dict.update(enclosed_data)
                    del cred_dict["@graph"]
                    break
        given_id = cred_dict.get("id")
        if given_id and self.check_if_cred_id_derived(given_id):
            given_id = str(uuid4())
        # issuer
        issuer = cred_dict.get("issuer")
        if type(issuer) is dict:
            issuer = issuer.get("id")

        # subjects
        subject_ids = None
        subjects = cred_dict.get("credentialSubject")
        if subjects:
            if type(subjects) is dict:
                subjects = [subjects]
            subject_ids = [
                subject.get("id") for subject in subjects if ("id" in subject)
            ]
        else:
            cred_dict["credentialSubject"] = {}

        # Schemas
        schemas = cred_dict.get("credentialSchema", [])
        if type(schemas) is dict:
            schemas = [schemas]
        schema_ids = [schema.get("id") for schema in schemas]
        expanded = jsonld.expand(cred_dict)
        types = JsonLdProcessor.get_values(
            expanded[0],
            "@type",
        )
        return VCRecord(
            contexts=contexts,
            expanded_types=types,
            issuer_id=issuer,
            subject_ids=subject_ids,
            proof_types=proof_types,
            given_id=given_id,
            cred_value=cred_dict,
            schema_ids=schema_ids,
        )

    def reveal_doc(self, credential_dict: dict, constraints: Constraints):
        """Generate reveal_doc dict for deriving credential."""
        derived = {
            "@context": credential_dict.get("@context"),
            "type": credential_dict.get("type"),
            "@explicit": True,
            "@requireAll": True,
            "issuanceDate": {},
            "issuer": {},
        }
        unflatten_dict = {}
        for field in constraints._fields:
            for path in field.paths:
                jsonpath = parse(path)
                match = jsonpath.find(credential_dict)
                if len(match) == 0:
                    continue
                for match_item in match:
                    full_path = str(match_item.full_path)
                    if bool(re.search(pattern=r"\[[0-9]+\]", string=full_path)):
                        full_path = full_path.replace(".[", "[")
                    unflatten_dict[full_path] = {}
                    explicit_key_path = None
                    key_list = full_path.split(".")[:-1]
                    for key in key_list:
                        if not explicit_key_path:
                            explicit_key_path = key
                        else:
                            explicit_key_path = explicit_key_path + "." + key
                        unflatten_dict[explicit_key_path + ".@explicit"] = True
                        unflatten_dict[explicit_key_path + ".@requireAll"] = True
        derived = self.new_credential_builder(derived, unflatten_dict)
        # Fix issue related to credentialSubject type property
        if "credentialSubject" in derived.keys():
            if "type" in credential_dict.get("credentialSubject"):
                derived["credentialSubject"]["type"] = credential_dict.get(
                    "credentialSubject"
                ).get("type")
        if "credentialSubject" not in derived.keys():
            if isinstance(credential_dict.get("credentialSubject"), list):
                derived["credentialSubject"] = []
            elif isinstance(credential_dict.get("credentialSubject"), dict):
                derived["credentialSubject"] = {}
        return derived

    def new_credential_builder(
        self, new_credential: dict, unflatten_dict: dict
    ) -> dict:
        """
        Update and return the new_credential.

        Args:
            new_credential: credential dict to be updated and returned
            unflatten_dict: dict with traversal path as key and match_value as value
        Return:
            dict

        """
        new_credential.update(unflatten(unflatten_dict))
        return new_credential

    async def filter_by_field(self, field: DIFField, credential: VCRecord) -> bool:
        """
        Apply filter on VCRecord.

        Checks if a credential is applicable

        Args:
            field: Field contains filtering spec
            credential: credential to apply filtering on
        Return:
            bool

        """
        credential_dict = credential.cred_value
        for path in field.paths:
            if "$.proof." in path:
                raise DIFPresExchError(
                    "JSON Path expression matching on proof object "
                    "is not currently supported"
                )
            jsonpath = parse(path)
            match = jsonpath.find(credential_dict)
            if len(match) == 0:
                continue
            for match_item in match:
                # No filter in constraint
                if not field._filter:
                    return True
                if self.validate_patch(match_item.value, field._filter):
                    return True
        return False

    def validate_patch(self, to_check: any, _filter: Filter) -> bool:
        """
        Apply filter on match_value.

        Utility function used in applying filtering to a cred
        by triggering checks according to filter specification

        Args:
            to_check: value to check, extracted from match
            _filter: Filter
        Return:
            bool

        """
        return_val = False
        if _filter._type:
            if self.check_filter_only_type_enforced(_filter):
                if _filter._type == "number":
                    if isinstance(to_check, (int, float)):
                        return True
                elif _filter._type == "string":
                    if isinstance(to_check, str):
                        if _filter.fmt == "date" or _filter.fmt == "date-time":
                            try:
                                to_compare_date = dateutil_parser(to_check)
                                if isinstance(to_compare_date, datetime):
                                    return True
                            except (ParserError, TypeError):
                                return False
                        else:
                            return True
            else:
                if _filter._type == "number":
                    return_val = self.process_numeric_val(to_check, _filter)
                elif _filter._type == "string":
                    return_val = self.process_string_val(to_check, _filter)
        else:
            if _filter.enums:
                return_val = self.enum_check(val=to_check, _filter=_filter)
            if _filter.const:
                return_val = self.const_check(val=to_check, _filter=_filter)

        if _filter._not:
            return not return_val
        return return_val

    def check_filter_only_type_enforced(self, _filter: Filter) -> bool:
        """
        Check if only type is specified in filter.

        Args:
            _filter: Filter
        Return:
            bool

        """
        if (
            _filter.pattern is None
            and _filter.minimum is None
            and _filter.maximum is None
            and _filter.min_length is None
            and _filter.max_length is None
            and _filter.exclusive_min is None
            and _filter.exclusive_max is None
            and _filter.const is None
            and _filter.enums is None
        ):
            return True
        else:
            return False

    def process_numeric_val(self, val: any, _filter: Filter) -> bool:
        """
        Trigger Filter checks.

        Trigger appropriate check for a number type filter,
        according to _filter spec.

        Args:
            val: value to check, extracted from match
            _filter: Filter
        Return:
            bool

        """
        if _filter.exclusive_max:
            return self.exclusive_maximum_check(val, _filter)
        elif _filter.exclusive_min:
            return self.exclusive_minimum_check(val, _filter)
        elif _filter.minimum:
            return self.minimum_check(val, _filter)
        elif _filter.maximum:
            return self.maximum_check(val, _filter)
        elif _filter.const:
            return self.const_check(val, _filter)
        elif _filter.enums:
            return self.enum_check(val, _filter)
        else:
            return False

    def process_string_val(self, val: any, _filter: Filter) -> bool:
        """
        Trigger Filter checks.

        Trigger appropriate check for a string type filter,
        according to _filter spec.

        Args:
            val: value to check, extracted from match
            _filter: Filter
        Return:
            bool

        """
        if _filter.min_length or _filter.max_length:
            return self.length_check(val, _filter)
        elif _filter.pattern:
            return self.pattern_check(val, _filter)
        elif _filter.enums:
            return self.enum_check(val, _filter)
        elif _filter.exclusive_max and _filter.fmt:
            return self.exclusive_maximum_check(val, _filter)
        elif _filter.exclusive_min and _filter.fmt:
            return self.exclusive_minimum_check(val, _filter)
        elif _filter.minimum and _filter.fmt:
            return self.minimum_check(val, _filter)
        elif _filter.maximum and _filter.fmt:
            return self.maximum_check(val, _filter)
        elif _filter.const:
            return self.const_check(val, _filter)
        else:
            return False

    def exclusive_minimum_check(self, val: any, _filter: Filter) -> bool:
        """
        Exclusiveminimum check.

        Returns True if value greater than filter specified check

        Args:
            val: value to check, extracted from match
            _filter: Filter
        Return:
            bool

        """
        try:
            if _filter.fmt:
                utc = pytz.UTC
                if _filter.fmt == "date" or _filter.fmt == "date-time":
                    to_compare_date = dateutil_parser(_filter.exclusive_min).replace(
                        tzinfo=utc
                    )
                    given_date = dateutil_parser(str(val)).replace(tzinfo=utc)
                    return given_date > to_compare_date
            else:
                if self.is_numeric(val):
                    return val > _filter.exclusive_min
            return False
        except (TypeError, ValueError, ParserError):
            return False

    def exclusive_maximum_check(self, val: any, _filter: Filter) -> bool:
        """
        Exclusivemaximum check.

        Returns True if value less than filter specified check

        Args:
            val: value to check, extracted from match
            _filter: Filter
        Return:
            bool

        """
        try:
            if _filter.fmt:
                utc = pytz.UTC
                if _filter.fmt == "date" or _filter.fmt == "date-time":
                    to_compare_date = dateutil_parser(_filter.exclusive_max).replace(
                        tzinfo=utc
                    )
                    given_date = dateutil_parser(str(val)).replace(tzinfo=utc)
                    return given_date < to_compare_date
            else:
                if self.is_numeric(val):
                    return val < _filter.exclusive_max
            return False
        except (TypeError, ValueError, ParserError):
            return False

    def maximum_check(self, val: any, _filter: Filter) -> bool:
        """
        Maximum check.

        Returns True if value less than equal to filter specified check

        Args:
            val: value to check, extracted from match
            _filter: Filter
        Return:
            bool

        """
        try:
            if _filter.fmt:
                utc = pytz.UTC
                if _filter.fmt == "date" or _filter.fmt == "date-time":
                    to_compare_date = dateutil_parser(_filter.maximum).replace(
                        tzinfo=utc
                    )
                    given_date = dateutil_parser(str(val)).replace(tzinfo=utc)
                    return given_date <= to_compare_date
            else:
                if self.is_numeric(val):
                    return val <= _filter.maximum
            return False
        except (TypeError, ValueError, ParserError):
            return False

    def minimum_check(self, val: any, _filter: Filter) -> bool:
        """
        Minimum check.

        Returns True if value greater than equal to filter specified check

        Args:
            val: value to check, extracted from match
            _filter: Filter
        Return:
            bool

        """
        try:
            if _filter.fmt:
                utc = pytz.UTC
                if _filter.fmt == "date" or _filter.fmt == "date-time":
                    to_compare_date = dateutil_parser(_filter.minimum).replace(
                        tzinfo=utc
                    )
                    given_date = dateutil_parser(str(val)).replace(tzinfo=utc)
                    return given_date >= to_compare_date
            else:
                if self.is_numeric(val):
                    return val >= _filter.minimum
            return False
        except (TypeError, ValueError, ParserError):
            return False

    def length_check(self, val: any, _filter: Filter) -> bool:
        """
        Length check.

        Returns True if length value string meets the minLength and maxLength specs

        Args:
            val: value to check, extracted from match
            _filter: Filter
        Return:
            bool

        """
        given_len = len(str(val))
        if _filter.max_length and _filter.min_length:
            if given_len <= _filter.max_length and given_len >= _filter.min_length:
                return True
        elif _filter.max_length and not _filter.min_length:
            if given_len <= _filter.max_length:
                return True
        elif not _filter.max_length and _filter.min_length:
            if given_len >= _filter.min_length:
                return True
        return False

    def pattern_check(self, val: any, _filter: Filter) -> bool:
        """
        Pattern check.

        Returns True if value string matches the specified pattern

        Args:
            val: value to check, extracted from match
            _filter: Filter
        Return:
            bool

        """
        if _filter.pattern:
            return bool(re.search(pattern=_filter.pattern, string=str(val)))
        return False

    def const_check(self, val: any, _filter: Filter) -> bool:
        """
        Const check.

        Returns True if value is equal to filter specified check

        Args:
            val: value to check, extracted from match
            _filter: Filter
        Return:
            bool

        """
        if val == _filter.const:
            return True
        return False

    def enum_check(self, val: any, _filter: Filter) -> bool:
        """
        Enum check.

        Returns True if value is contained to filter specified list

        Args:
            val: value to check, extracted from match
            _filter: Filter
        Return:
            bool

        """
        if val in _filter.enums:
            return True
        return False

    def subject_is_issuer(self, credential: VCRecord) -> bool:
        """
        subject_is_issuer check.

        Returns True if cred issuer_id is in subject_ids

        Args:
            credential: VCRecord
        Return:
            bool

        """
        subject_ids = credential.subject_ids
        for subject_id in subject_ids:
            issuer_id = credential.issuer_id
            if subject_id != "" and subject_id == issuer_id:
                return True
        return False

    async def filter_schema(
        self, credentials: Sequence[VCRecord], schemas: Sequence[SchemaInputDescriptor]
    ) -> Sequence[VCRecord]:
        """
        Filter by schema.

        Returns list of credentials where credentialSchema.id or types matched
        with input_descriptors.schema.uri

        Args:
            credentials: list of VCRecords to check
            schemas: list of schemas from the input_descriptors
        Return:
            Sequence of filtered VCRecord

        """
        result = []
        for credential in credentials:
            applicable = False
            for schema in schemas:
                applicable = self.credential_match_schema(
                    credential=credential, schema_id=schema.uri
                )
                if schema.required and not applicable:
                    break
                if applicable:
                    if schema.uri in [
                        EXPANDED_TYPE_CREDENTIALS_CONTEXT_V1_VC_TYPE,
                    ]:
                        continue
                    else:
                        break
            if applicable:
                result.append(credential)
        return result

    def credential_match_schema(self, credential: VCRecord, schema_id: str) -> bool:
        """
        Credential matching by schema.

        Used by filter_schema to check if credential.schema_ids or credential.types
        matched with schema_id

        Args:
            credential: VCRecord to check
            schema_id: schema uri to check
        Return:
            bool
        """
        if schema_id in credential.schema_ids:
            return True
        if schema_id in credential.expanded_types:
            return True
        return False

    async def filter_creds_record_id(
        self, credentials: Sequence[VCRecord], records_list: Sequence[str]
    ) -> Sequence[VCRecord]:
        """Return filtered list of credentials using records_list."""
        filtered_cred = []
        for credential in credentials:
            if credential.record_id in records_list:
                filtered_cred.append(credential)
        return filtered_cred

    async def apply_requirements(
        self,
        req: Requirement,
        credentials: Sequence[VCRecord],
        records_filter: dict = None,
    ) -> dict:
        """
        Apply Requirement.

        Args:
            req: Requirement
            credentials: Sequence of credentials to check against
        Return:
            dict of input_descriptor ID key to list of credential_json
        """
        # Dict for storing descriptor_id keys and list of applicable
        # credentials values
        result = {}
        # Get all input_descriptors attached to the PresentationDefinition
        descriptor_list = req.input_descriptors or []
        for descriptor in descriptor_list:
            # Filter credentials to apply filtering
            # upon by matching each credentialSchema.id
            # or expanded types on each InputDescriptor's schema URIs
            if records_filter and (descriptor.id in records_filter):
                filtered_creds_by_descriptor_id = await self.filter_creds_record_id(
                    credentials, records_filter.get(descriptor.id)
                )
                filtered_by_schema = await self.filter_schema(
                    credentials=filtered_creds_by_descriptor_id,
                    schemas=descriptor.schemas,
                )
            else:
                filtered_by_schema = await self.filter_schema(
                    credentials=credentials, schemas=descriptor.schemas
                )
            # Filter credentials based upon path expressions specified in constraints
            filtered = await self.filter_constraints(
                constraints=descriptor.constraint,
                credentials=filtered_by_schema,
            )
            if len(filtered) != 0:
                result[descriptor.id] = filtered

        if len(descriptor_list) != 0:
            # Applies min, max or count attributes of submission_requirement
            if self.is_len_applicable(req, len(result)):
                return result
            return {}

        nested_result = []
        cred_uid_descriptors = {}
        # recursion logic for nested requirements
        for requirement in req.nested_req:
            # recursive call
            result = await self.apply_requirements(
                requirement, credentials, records_filter
            )
            if result == {}:
                continue
            # cred_uid_descriptors maps applicable credentials
            # to their respective descriptor.
            # Structure: {cred.given_id: {
            #           desc_id_1: {}
            #      },
            #      ......
            # }
            #  This will be used to construct exclude dict.
            for descriptor_id in result.keys():
                credential_list = result.get(descriptor_id)
                for credential in credential_list:
                    cred_id = credential.given_id or credential.record_id
                    if cred_id:
                        cred_uid_descriptors.setdefault(cred_id, {})[descriptor_id] = {}

            if len(result.keys()) != 0:
                nested_result.append(result)

        exclude = {}
        for uid in cred_uid_descriptors.keys():
            # Check if number of applicable credentials
            # does not meet requirement specification
            if not self.is_len_applicable(req, len(cred_uid_descriptors[uid])):
                for descriptor_id in cred_uid_descriptors[uid]:
                    # Add to exclude dict
                    # with cred_uid + descriptor_id as key
                    exclude[descriptor_id + uid] = {}
        # merging credentials and excluding credentials that don't satisfy the requirement
        return await self.merge_nested_results(
            nested_result=nested_result, exclude=exclude
        )

    def is_numeric(self, val: any) -> bool:
        """
        Check if val is an int or float.

        Args:
            val: to check
        Return:
            bool
        """
        if isinstance(val, float) or isinstance(val, int):
            return True
        else:
            return False

    async def merge_nested_results(
        self, nested_result: Sequence[dict], exclude: dict
    ) -> dict:
        """
        Merge nested results with merged credentials.

        Args:
            nested_result: Sequence of dict containing input_descriptor.id as keys
                and list of creds as values
            exclude: dict containing info about credentials to exclude
        Return:
            dict with input_descriptor.id as keys and merged_credentials_list as values
        """
        result = {}
        for res in nested_result:
            for key in res.keys():
                credentials = res[key]
                uid_dict = {}
                merged_credentials = []

                if key in result:
                    for credential in result[key]:
                        cred_id = credential.given_id or credential.record_id
                        if cred_id and cred_id not in uid_dict:
                            merged_credentials.append(credential)
                            uid_dict[cred_id] = {}

                for credential in credentials:
                    cred_id = credential.given_id or credential.record_id
                    if cred_id and cred_id not in uid_dict:
                        if (key + cred_id) not in exclude:
                            merged_credentials.append(credential)
                            uid_dict[cred_id] = {}
                result[key] = merged_credentials
        return result

    async def create_vp(
        self,
        credentials: Sequence[VCRecord],
        pd: PresentationDefinition,
        challenge: str = None,
        domain: str = None,
        records_filter: dict = None,
    ) -> dict:
        """
        Create VerifiablePresentation.

        Args:
            credentials: Sequence of VCRecords
            pd: PresentationDefinition
        Return:
            VerifiablePresentation
        """
        document_loader = self.profile.inject(DocumentLoader)
        req = await self.make_requirement(
            srs=pd.submission_requirements, descriptors=pd.input_descriptors
        )
        result = await self.apply_requirements(
            req=req, credentials=credentials, records_filter=records_filter
        )
        applicable_creds, descriptor_maps = await self.merge(result)
        applicable_creds_list = []
        for credential in applicable_creds:
            applicable_creds_list.append(credential.cred_value)
        if (
            not self.profile.settings.get("debug.auto_respond_presentation_request")
            and not records_filter
            and len(applicable_creds_list) > 1
        ):
            raise DIFPresExchError(
                "Multiple credentials are applicable for presentation_definition "
                f"{pd.id} and --auto-respond-presentation-request setting is not "
                "enabled. Please specify which credentials should be applied to "
                "which input_descriptors using record_ids filter."
            )
        # submission_property
        submission_property = PresentationSubmission(
            id=str(uuid4()), definition_id=pd.id, descriptor_maps=descriptor_maps
        )
        if self.check_sign_pres(applicable_creds):
            (
                issuer_id,
                filtered_creds_list,
            ) = await self.get_sign_key_credential_subject_id(
                applicable_creds=applicable_creds
            )
            if not issuer_id and len(filtered_creds_list) == 0:
                vp = await create_presentation(credentials=applicable_creds_list)
                vp["presentation_submission"] = submission_property.serialize()
                if self.proof_type is BbsBlsSignature2020.signature_type:
                    vp["@context"].append(SECURITY_CONTEXT_BBS_URL)
                return vp
            else:
                vp = await create_presentation(credentials=filtered_creds_list)
                vp["presentation_submission"] = submission_property.serialize()
                if self.proof_type is BbsBlsSignature2020.signature_type:
                    vp["@context"].append(SECURITY_CONTEXT_BBS_URL)
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                issue_suite = await self._get_issue_suite(
                    wallet=wallet,
                    issuer_id=issuer_id,
                )
                signed_vp = await sign_presentation(
                    presentation=vp,
                    suite=issue_suite,
                    challenge=challenge,
                    document_loader=document_loader,
                )
                return signed_vp
        else:
            vp = await create_presentation(credentials=applicable_creds_list)
            vp["presentation_submission"] = submission_property.serialize()
            if self.proof_type is BbsBlsSignature2020.signature_type:
                vp["@context"].append(SECURITY_CONTEXT_BBS_URL)
            if self.pres_signing_did:
                async with self.profile.session() as session:
                    wallet = session.inject(BaseWallet)
                    issue_suite = await self._get_issue_suite(
                        wallet=wallet,
                        issuer_id=self.pres_signing_did,
                    )
                    signed_vp = await sign_presentation(
                        presentation=vp,
                        suite=issue_suite,
                        challenge=challenge,
                        document_loader=document_loader,
                    )
                    return signed_vp
            else:
                return vp

    def check_sign_pres(self, creds: Sequence[VCRecord]) -> bool:
        """Check if applicable creds have CredentialSubject.id set."""
        for cred in creds:
            if len(cred.subject_ids) > 0 and not self.check_if_cred_id_derived(
                next(iter(cred.subject_ids))
            ):
                return True
        return False

    def check_if_cred_id_derived(self, id: str) -> bool:
        """Check if credential or credentialSubjet id is derived."""
        if id.startswith("urn:bnid:_:c14n"):
            return True
        return False

    async def merge(
        self,
        dict_descriptor_creds: dict,
    ) -> (Sequence[VCRecord], Sequence[InputDescriptorMapping]):
        """
        Return applicable credentials and descriptor_map for attachment.

        Used for generating the presentation_submission property with the
        descriptor_map, mantaining the order in which applicable credential
        list is returned.

        Args:
            dict_descriptor_creds: dict with input_descriptor.id as keys
            and merged_credentials_list
        Return:
            Tuple of applicable credential list and descriptor map
        """
        dict_of_creds = {}
        dict_of_descriptors = {}
        result = []
        descriptors = []
        sorted_desc_keys = sorted(list(dict_descriptor_creds.keys()))
        for desc_id in sorted_desc_keys:
            credentials = dict_descriptor_creds.get(desc_id)
            for cred in credentials:
                cred_id = cred.given_id or cred.record_id
                if cred_id:
                    if cred_id not in dict_of_creds:
                        result.append(cred)
                        dict_of_creds[cred_id] = len(descriptors)
                    if f"{cred_id}-{cred_id}" not in dict_of_descriptors:
                        descriptor_map = InputDescriptorMapping(
                            id=desc_id,
                            fmt="ldp_vp",
                            path=(f"$.verifiableCredential[{dict_of_creds[cred_id]}]"),
                        )
                        descriptors.append(descriptor_map)

        descriptors = sorted(descriptors, key=lambda i: i.id)
        return (result, descriptors)

    async def verify_received_pres(
        self,
        pd: PresentationDefinition,
        pres: dict,
    ):
        """
        Verify credentials received in presentation.

        Args:
            pres: received VerifiablePresentation
            pd: PresentationDefinition
        """
        descriptor_map_list = pres.get("presentation_submission").get("descriptor_map")
        input_descriptors = pd.input_descriptors
        inp_desc_id_contraint_map = {}
        for input_descriptor in input_descriptors:
            inp_desc_id_contraint_map[input_descriptor.id] = input_descriptor.constraint
        for desc_map_item in descriptor_map_list:
            desc_map_item_id = desc_map_item.get("id")
            constraint = inp_desc_id_contraint_map.get(desc_map_item_id)
            desc_map_item_path = desc_map_item.get("path")
            jsonpath = parse(desc_map_item_path)
            match = jsonpath.find(pres)
            if len(match) == 0:
                raise DIFPresExchError(
                    f"{desc_map_item_path} path in descriptor_map not applicable"
                )
            for match_item in match:
                if not await self.apply_constraint_received_cred(
                    constraint, match_item.value
                ):
                    raise DIFPresExchError(
                        f"Constraint specified for {desc_map_item_id} does not "
                        f"apply to the enclosed credential in {desc_map_item_path}"
                    )

    async def apply_constraint_received_cred(
        self, constraint: Constraints, cred_dict: dict
    ) -> bool:
        """Evaluate constraint from the request against received credential."""
        fields = constraint._fields
        field_paths = []
        credential = self.create_vcrecord(cred_dict)
        for field in fields:
            field_paths = field_paths + field.paths
            if not await self.filter_by_field(field, credential):
                return False
        # Selective Disclosure check
        if constraint.limit_disclosure == "required":
            field_paths = set([path.replace("$.", "") for path in field_paths])
            mandatory_paths = {
                "@context",
                "type",
                "issuanceDate",
                "issuer",
                "proof",
                "credentialSubject",
                "id",
            }
            to_remove_from_field_paths = set()
            nested_field_paths = {"credentialSubject": {"id", "type"}}
            for field_path in field_paths:
                if field_path.count(".") >= 1:
                    split_field_path = field_path.split(".")
                    key = ".".join(split_field_path[:-1])
                    value = split_field_path[-1]
                    nested_field_paths = self.build_nested_paths_dict(
                        key, value, nested_field_paths
                    )
                    to_remove_from_field_paths.add(field_path)
            for to_remove_path in to_remove_from_field_paths:
                field_paths.remove(to_remove_path)

            field_paths = set.union(mandatory_paths, field_paths)

            for attrs in cred_dict.keys():
                if attrs not in field_paths:
                    return False
            for nested_attr_key in nested_field_paths:
                nested_attr_values = nested_field_paths[nested_attr_key]
                split_nested_attr_key = nested_attr_key.split(".")
                extracted_dict = self.nested_get(cred_dict, split_nested_attr_key)
                for attrs in extracted_dict.keys():
                    if attrs not in nested_attr_values:
                        return False
        return True

    def nested_get(self, input_dict: dict, nested_key: Sequence[str]) -> dict:
        """Return internal dict from nested input_dict given list of nested_key."""
        internal_dict_value = input_dict
        for k in nested_key:
            internal_dict_value = internal_dict_value.get(k, None)
        return internal_dict_value

    def build_nested_paths_dict(
        self, key: str, value: str, nested_field_paths: dict
    ) -> dict:
        """Build and return nested_field_paths dict."""
        if key in nested_field_paths.keys():
            nested_field_paths[key].add(value)
        else:
            nested_field_paths[key] = {value}
        split_key = key.split(".")
        if len(split_key) > 1:
            nested_field_paths.update(
                self.build_nested_paths_dict(
                    ".".join(split_key[:-1]), split_key[-1], nested_field_paths
                )
            )
        return nested_field_paths
