"""
Utilities for dif presentation exchange attachment.

General Flow:
create_vp ->
make_requirement [create a Requirement from SubmissionRequirements and Descriptors] ->
apply_requirement [filter credentials] ->
merge [return applicable credential list and descriptor_map for presentation_submission]
returns VerifiablePresentation
"""
import json
import pytz
import re

from dateutil.parser import parse as dateutil_parser
from jsonpath_ng import parse
from typing import Sequence, Optional
from uuid import uuid4

from ....core.error import BaseError
from ....storage.vc_holder.vc_record import VCRecord

from .pres_exch import (
    PresentationDefinition,
    InputDescriptors,
    Field,
    Filter,
    Constraints,
    SubmissionRequirements,
    Requirement,
    SchemaInputDescriptor,
    VerifiablePresentation,
    InputDescriptorMapping,
    PresentationSubmission,
)


class PresentationExchError(BaseError):
    """Base class for DIF Presentation Exchange related errors."""


CREDENTIAL_JSONLD_CONTEXT = "https://www.w3.org/2018/credentials/v1"
PRESENTATION_SUBMISSION_JSONLD_CONTEXT = (
    "https://identity.foundation/presentation-exchange/submission/v1"
)
VERIFIABLE_PRESENTATION_JSONLD_TYPE = "VerifiablePresentation"
PRESENTATION_SUBMISSION_JSONLD_TYPE = "PresentationSubmission"


async def to_requirement(
    sr: SubmissionRequirements, descriptors: Sequence[InputDescriptors]
) -> Requirement:
    """
    Return Requirement.

    Args:
        sr: submission_requirement
        descriptors: list of input_descriptors
    Raises:
        PresentationExchError: If not able to create requirement

    """
    input_descriptors = []
    nested = []
    total_count = 0

    if sr._from:
        if sr._from != "":
            for descriptor in descriptors:
                if contains(descriptor.groups, sr._from):
                    input_descriptors.append(descriptor)
            total_count = len(input_descriptors)
            if total_count == 0:
                raise PresentationExchError(f"No descriptors for from: {sr._from}")
    else:
        for submission_requirement in sr.from_nested:
            try:
                # recursion logic
                requirement = await to_requirement(submission_requirement, descriptors)
                nested.append(requirement)
            except Exception as err:
                raise PresentationExchError(
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
        PresentationExchError: If not able to create requirement

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
                await to_requirement(submission_requirement, descriptors)
            )
        except Exception as err:
            raise PresentationExchError(
                f"Error creating requirement inside to_requirement function, {err}"
            )
    return requirement


def is_len_applicable(req: Requirement, val: int) -> bool:
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


def contains(data: Sequence[str], e: str) -> bool:
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
    constraints: Constraints, credentials: Sequence[VCRecord]
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
    result = []
    for credential in credentials:
        if constraints.subject_issuer == "required" and not await subject_is_issuer(
            credential=credential
        ):
            continue

        applicable = False
        predicate = False
        for field in constraints._fields:
            applicable = await filter_by_field(field, credential)
            if field.predicate == "required":
                predicate = True
            if applicable:
                break
        if not applicable:
            continue

        # TODO: create new credential with selective disclosure
        if constraints.limit_disclosure or predicate:
            raise PresentationExchError("Not yet implemented - createNewCredential")

        result.append(credential)
    return result


async def filter_by_field(field: Field, credential: VCRecord) -> bool:
    """
    Apply filter on VCRecord.

    Checks if a credential is applicable

    Args:
        field: Field contains filtering spec
        credential: credential to apply filtering on
    Return:
        bool

    """
    credential_dict = json.loads(credential.value)
    for path in field.paths:
        jsonpath = parse(path)
        match = jsonpath.find(credential_dict)
        if len(match) == 0:
            continue
        for match_item in match:
            if validate_patch(match_item.value, field._filter):
                return True
    return False


def validate_patch(to_check: any, _filter: Filter) -> bool:
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
    return_val = None
    if _filter._type:
        if _filter._type == "number":
            return_val = process_numeric_val(to_check, _filter)
        elif _filter._type == "string":
            return_val = process_string_val(to_check, _filter)
    else:
        if _filter.enums:
            return_val = enum_check(val=to_check, _filter=_filter)
        if _filter.const:
            return_val = const_check(val=to_check, _filter=_filter)

    if _filter._not:
        return not return_val
    else:
        return return_val


def process_numeric_val(val: any, _filter: Filter) -> bool:
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
        return exclusive_maximum_check(val, _filter)
    elif _filter.exclusive_min:
        return exclusive_minimum_check(val, _filter)
    elif _filter.minimum:
        return minimum_check(val, _filter)
    elif _filter.maximum:
        return maximum_check(val, _filter)
    elif _filter.const:
        return const_check(val, _filter)
    elif _filter.enums:
        return enum_check(val, _filter)
    else:
        return False


def process_string_val(val: any, _filter: Filter) -> bool:
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
        return length_check(val, _filter)
    elif _filter.pattern:
        return pattern_check(val, _filter)
    elif _filter.enums:
        return enum_check(val, _filter)
    elif _filter.exclusive_max:
        if _filter.fmt:
            return exclusive_maximum_check(val, _filter)
    elif _filter.exclusive_min:
        if _filter.fmt:
            return exclusive_minimum_check(val, _filter)
    elif _filter.minimum:
        if _filter.fmt:
            return minimum_check(val, _filter)
    elif _filter.maximum:
        if _filter.fmt:
            return maximum_check(val, _filter)
    elif _filter.const:
        return const_check(val, _filter)
    else:
        return False


def exclusive_minimum_check(val: any, _filter: Filter) -> bool:
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
            if is_numeric(val):
                return val > _filter.exclusive_min
        return False
    except (TypeError, ValueError):
        return False


def exclusive_maximum_check(val: any, _filter: Filter) -> bool:
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
            if is_numeric(val):
                return val < _filter.exclusive_max
        return False
    except (TypeError, ValueError):
        return False


def maximum_check(val: any, _filter: Filter) -> bool:
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
                to_compare_date = dateutil_parser(_filter.maximum).replace(tzinfo=utc)
                given_date = dateutil_parser(str(val)).replace(tzinfo=utc)
                return given_date <= to_compare_date
        else:
            if is_numeric(val):
                return val <= _filter.maximum
        return False
    except (TypeError, ValueError):
        return False


def minimum_check(val: any, _filter: Filter) -> bool:
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
                to_compare_date = dateutil_parser(_filter.minimum).replace(tzinfo=utc)
                given_date = dateutil_parser(str(val)).replace(tzinfo=utc)
                return given_date >= to_compare_date
        else:
            if is_numeric(val):
                return val >= _filter.minimum
        return False
    except (TypeError, ValueError):
        return False


def length_check(val: any, _filter: Filter) -> bool:
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


def pattern_check(val: any, _filter: Filter) -> bool:
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


def const_check(val: any, _filter: Filter) -> bool:
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


def enum_check(val: any, _filter: Filter) -> bool:
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


async def subject_is_issuer(credential: VCRecord) -> bool:
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
    credentials: Sequence[VCRecord], schemas: Sequence[SchemaInputDescriptor]
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
            applicable = await credential_match_schema(
                credential=credential, schema_id=schema.uri
            )
            if schema.required and not applicable:
                break
        if applicable:
            result.append(credential)
    return result


async def credential_match_schema(credential: VCRecord, schema_id: str) -> bool:
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
    for cred_schema_id in credential.schema_ids:
        if cred_schema_id == schema_id:
            return True
    for cred_type in credential.types:
        if cred_type == schema_id:
            return True
    return False


async def apply_requirements(req: Requirement, credentials: Sequence[VCRecord]) -> dict:
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
        # Filter credentials to apply filtering upon by matching each credentialSchema.id
        # or expanded types on each InputDescriptor's schema URIs
        filtered_by_schema = await filter_schema(
            credentials=credentials, schemas=descriptor.schemas
        )
        # Filter credentials based upon path expressions specified in constraints
        filtered = await filter_constraints(
            constraints=descriptor.constraint, credentials=filtered_by_schema
        )
        if len(filtered) != 0:
            result[descriptor._id] = filtered

    if len(descriptor_list) != 0:
        # Applies min, max or count attributes of submission_requirement
        if is_len_applicable(req, len(result)):
            return result
        return {}

    nested_result = []
    given_id_descriptors = {}
    # recursion logic for nested requirements
    for requirement in req.nested_req:
        # recursive call
        result = await apply_requirements(requirement, credentials)
        if result == {}:
            continue
        # tmp_dict maps applicable credentials to their respective descriptor.
        # Structure: {cred.given_id: {
        #           desc_id_1: {}
        #      },
        #      ......
        # }
        #  This will be used to construct exclude dict.
        for descriptor_id in result.keys():
            credential_list = result.get(descriptor_id)
            for credential in credential_list:
                if credential.given_id not in given_id_descriptors:
                    tmp_dict[credential.given_id] = {}
                tmp_dict[credential.given_id][descriptor_id] = {}

        if len(result.keys()) != 0:
            nested_result.append(result)

    exclude = {}
    for given_id in given_id_descriptors.keys():
        # Check if number of applicable credentials
        # does not meet requirement specification
        if not is_len_applicable(req, len(given_id_descriptors[k])):
            for descriptor_id in given_id_descriptors[given_id]:
                # Add to exclude dict
                # with cred.given_id + descriptor_id as key
                exclude[descriptor_id + k] = {}
    # merging credentials and excluding credentials that don't satisfy the requirement
    return await merge_nested_results(nested_result=nested_result, exclude=exclude)


def is_numeric(val: any) -> bool:
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


async def merge_nested_results(nested_result: Sequence[dict], exclude: dict) -> dict:
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
            tmp_dict = {}
            merged_credentials = []

            if key in result:
                for credential in result[key]:
                    if credential.given_id not in tmp_dict:
                        merged_credentials.append(credential)
                        tmp_dict[credential.given_id] = {}

            for credential in credentials:
                if credential.given_id not in tmp_dict:
                    if (key + (credential.given_id)) not in exclude:
                        merged_credentials.append(credential)
                        tmp_dict[credential.given_id] = {}
            result[key] = merged_credentials
    return result


async def create_vp(
    credentials: Sequence[VCRecord], pd: PresentationDefinition
) -> Optional[VerifiablePresentation]:
    """
    Create VerifiablePresentation.

    Args:
        credentials: Sequence of VCRecords
        pd: PresentationDefinition
    Return:
        VerifiablePresentation
    """
    req = await make_requirement(
        srs=pd.submission_requirements, descriptors=pd.input_descriptors
    )
    result = await apply_requirements(req=req, credentials=credentials)
    applicable_creds, descriptor_maps = await merge(result)
    # convert list of verifiable credentials to list to dict
    applicable_cred_dict = []
    for credential in applicable_creds:
        applicable_cred_dict.append(json.loads(credential.value))
    # submission_property
    submission_property = PresentationSubmission(
        _id=str(uuid4()), definition_id=pd._id, descriptor_maps=descriptor_maps
    )

    # defaultVPContext
    default_vp_context = [
        CREDENTIAL_JSONLD_CONTEXT,
        PRESENTATION_SUBMISSION_JSONLD_CONTEXT,
    ]
    # defaultVPType
    default_vp_type = [
        VERIFIABLE_PRESENTATION_JSONLD_TYPE,
        PRESENTATION_SUBMISSION_JSONLD_TYPE,
    ]

    vp = VerifiablePresentation(
        _id=str(uuid4()),
        contexts=default_vp_context,
        types=default_vp_type,
        credentials=applicable_cred_dict,
        presentation_submission=submission_property,
    )
    return vp


async def merge(
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
        for credential in credentials:
            if credential.given_id not in dict_of_creds:
                result.append(credential)
                dict_of_creds[credential.given_id] = len(descriptors)

            if (
                f"{credential.given_id}-{credential.given_id}"
                not in dict_of_descriptors
            ):
                descriptor_map = InputDescriptorMapping(
                    _id=desc_id,
                    fmt="ldp_vp",
                    path=f"$.verifiableCredential[{dict_of_creds[credential.given_id]}]",
                )
                descriptors.append(descriptor_map)

    descriptors = sorted(descriptors, key=lambda i: i._id)
    return (result, descriptors)
