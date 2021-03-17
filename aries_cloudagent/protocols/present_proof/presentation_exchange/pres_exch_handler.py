"""Utilities for dif presentation exchange attachment."""
import json
import pytz
import re

from dateutil.parser import parse as dateutil_parser
from jsonpath_ng import parse
from typing import Sequence, Optional
from uuid import uuid4

from ....storage.vc_holder.vc_record import VCRecord

from .error import PresentationExchError
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
            for tmp_descriptor in descriptors:
                if await contains(tmp_descriptor.groups, sr._from):
                    input_descriptors.append(tmp_descriptor)
            total_count = len(input_descriptors)
            if total_count == 0:
                raise PresentationExchError(f"No descriptors for from: {sr._from}")
    else:
        for tmp_sub_req in sr.from_nested:
            try:
                # recursion logic
                tmp_req = await to_requirement(tmp_sub_req, descriptors)
                nested.append(tmp_req)
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
    for tmp_sub_req in srs:
        try:
            requirement.nested_req.append(
                await to_requirement(tmp_sub_req, descriptors)
            )
        except Exception as err:
            raise PresentationExchError(
                "Error creating requirement " f"inside to_requirement function, {err}"
            )
    return requirement


async def is_len_applicable(req: Requirement, val: int) -> bool:
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


async def contains(data: Sequence[str], e: str) -> bool:
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
    for tmp_item in data_list:
        if e == tmp_item:
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
    for tmp_cred in credentials:
        if (
            constraints.subject_issuer is not None
            and constraints.subject_issuer == "required"
            and not await subject_is_issuer(credential=tmp_cred)
        ):
            continue

        applicable = False
        predicate = False
        for tmp_field in constraints._fields:
            applicable = await filter_by_field(tmp_field, tmp_cred)
            if tmp_field.predicate:
                if tmp_field.predicate == "required":
                    predicate = True
            if applicable:
                break
        if not applicable:
            continue

        # TODO: create new credential with selective disclosure
        if constraints.limit_disclosure or predicate:
            raise PresentationExchError("Not yet implemented - createNewCredential")

        result.append(tmp_cred)
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
    for tmp_path in field.paths:
        tmp_jsonpath = parse(tmp_path)
        match = tmp_jsonpath.find(json.loads(credential.value))
        if len(match) == 0:
            continue
        for match_item in match:
            if await validate_patch(match_item.value, field._filter):
                return True
    return False


async def validate_patch(to_check: any, _filter: Filter) -> bool:
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
            return_val = await process_numeric_val(to_check, _filter)
        elif _filter._type == "string":
            return_val = await process_string_val(to_check, _filter)
    else:
        if _filter.enums:
            return_val = await enum_check(val=to_check, _filter=_filter)
        if _filter.const:
            return_val = await const_check(val=to_check, _filter=_filter)

    if _filter._not:
        return not return_val
    else:
        return return_val


async def process_numeric_val(val: any, _filter: Filter) -> bool:
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
        return await exclusive_maximum_check(val, _filter)
    elif _filter.exclusive_min:
        return await exclusive_minimum_check(val, _filter)
    elif _filter.minimum:
        return await minimum_check(val, _filter)
    elif _filter.maximum:
        return await maximum_check(val, _filter)
    elif _filter.const:
        return await const_check(val, _filter)
    elif _filter.enums:
        return await enum_check(val, _filter)
    else:
        return False


async def process_string_val(val: any, _filter: Filter) -> bool:
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
        return await length_check(val, _filter)
    elif _filter.pattern:
        return await pattern_check(val, _filter)
    elif _filter.enums:
        return await enum_check(val, _filter)
    elif _filter.exclusive_max:
        if _filter.fmt:
            return await exclusive_maximum_check(val, _filter)
    elif _filter.exclusive_min:
        if _filter.fmt:
            return await exclusive_minimum_check(val, _filter)
    elif _filter.minimum:
        if _filter.fmt:
            return await minimum_check(val, _filter)
    elif _filter.maximum:
        if _filter.fmt:
            return await maximum_check(val, _filter)
    elif _filter.const:
        return await const_check(val, _filter)
    else:
        return False


async def exclusive_minimum_check(val: any, _filter: Filter) -> bool:
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
                tmp_date = dateutil_parser(_filter.exclusive_min).replace(tzinfo=utc)
                val = dateutil_parser(str(val)).replace(tzinfo=utc)
                return val > tmp_date
        else:
            if await is_numeric(val):
                return val > _filter.exclusive_min
        return False
    except (TypeError, ValueError):
        return False


async def exclusive_maximum_check(val: any, _filter: Filter) -> bool:
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
                tmp_date = dateutil_parser(_filter.exclusive_max).replace(tzinfo=utc)
                val = dateutil_parser(str(val)).replace(tzinfo=utc)
                return val < tmp_date
        else:
            if await is_numeric(val):
                return val < _filter.exclusive_max
        return False
    except (TypeError, ValueError):
        return False


async def maximum_check(val: any, _filter: Filter) -> bool:
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
                tmp_date = dateutil_parser(_filter.maximum).replace(tzinfo=utc)
                val = dateutil_parser(str(val)).replace(tzinfo=utc)
                return val <= tmp_date
        else:
            if await is_numeric(val):
                return val <= _filter.maximum
        return False
    except (TypeError, ValueError):
        return False


async def minimum_check(val: any, _filter: Filter) -> bool:
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
                tmp_date = dateutil_parser(_filter.minimum).replace(tzinfo=utc)
                val = dateutil_parser(str(val)).replace(tzinfo=utc)
                return val >= tmp_date
        else:
            if await is_numeric(val):
                return val >= _filter.minimum
        return False
    except (TypeError, ValueError):
        return False


async def length_check(val: any, _filter: Filter) -> bool:
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


async def pattern_check(val: any, _filter: Filter) -> bool:
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


async def const_check(val: any, _filter: Filter) -> bool:
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


async def enum_check(val: any, _filter: Filter) -> bool:
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
    for tmp_subject_id in subject_ids:
        tmp_issuer_id = credential.issuer_id
        if tmp_subject_id != "" and tmp_subject_id == tmp_issuer_id:
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
    for tmp_cred in credentials:
        applicable = False
        for tmp_schema in schemas:
            applicable = await credential_match_schama(
                credential=tmp_cred, schema_id=tmp_schema.uri
            )
            if tmp_schema.required and not applicable:
                break
        if applicable:
            result.append(tmp_cred)
    return result


async def credential_match_schama(credential: VCRecord, schema_id: str) -> bool:
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
    result = {}
    descriptor_list = []
    if not req.input_descriptors:
        descriptor_list = []
    else:
        descriptor_list = req.input_descriptors
    for tmp_descriptor in descriptor_list:
        filtered_by_schema = await filter_schema(
            credentials=credentials, schemas=tmp_descriptor.schemas
        )
        filtered = await filter_constraints(
            constraints=tmp_descriptor.constraint, credentials=filtered_by_schema
        )
        if len(filtered) != 0:
            result[tmp_descriptor._id] = filtered

    if len(descriptor_list) != 0:
        if await is_len_applicable(req, len(result)):
            return result
        return {}

    nested_result = []
    tmp_dict = {}
    # recursion logic for nested requirements
    for tmp_req in req.nested_req:
        tmp_result = await apply_requirements(tmp_req, credentials)
        if tmp_result == {}:
            continue

        for tmp_desc_id in tmp_result.keys():
            tmp_creds_list = tmp_result.get(tmp_desc_id)
            for tmp_cred in tmp_creds_list:
                if await trim_tmp_id(tmp_cred.given_id) not in tmp_dict:
                    tmp_dict[await trim_tmp_id(tmp_cred.given_id)] = {}
                tmp_dict[await trim_tmp_id(tmp_cred.given_id)][
                    tmp_desc_id
                ] = tmp_cred.given_id

        if len(tmp_result.keys()) != 0:
            nested_result.append(tmp_result)

    exclude = {}
    for k in tmp_dict.keys():
        if not await is_len_applicable(req, len(tmp_dict[k])):
            for desc_id in tmp_dict[k]:
                exclude[desc_id + (tmp_dict[k][desc_id])] = {}
    return await merge_nested_results(nested_result=nested_result, exclude=exclude)


async def is_numeric(val: any) -> bool:
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


async def get_tmp_id(id: str) -> str:
    """
    Create a temporary id.

    Args:
        id: original id
    Return:
        temporary id string
    """
    return id + "tmp_unique_id_" + str(uuid4())


async def trim_tmp_id(id: str) -> str:
    """
    Extract and return original id from a temporary id.

    Args:
        id: temporary id
    Raises:
        ValueError: if tmp_unique_id_ not exists in id
    Return:
        temporary id string
    """
    try:
        tmp_index = id.index("tmp_unique_id_")
        return id[:tmp_index]
    except ValueError:
        return id


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
                for tmp_cred in result[key]:
                    if tmp_cred.given_id not in tmp_dict:
                        merged_credentials.append(tmp_cred)
                        tmp_dict[tmp_cred.given_id] = {}

            for tmp_cred in credentials:
                if tmp_cred.given_id not in tmp_dict:
                    if (key + (tmp_cred.given_id)) not in exclude:
                        merged_credentials.append(tmp_cred)
                        tmp_dict[tmp_cred.given_id] = {}
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
    for tmp_cred in applicable_creds:
        applicable_cred_dict.append(json.loads(tmp_cred.value))
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
        for tmp_cred in credentials:
            if tmp_cred.given_id not in dict_of_creds:
                result.append(tmp_cred)
                dict_of_creds[await trim_tmp_id(tmp_cred.given_id)] = len(descriptors)

            if f"{tmp_cred.given_id}-{tmp_cred.given_id}" not in dict_of_descriptors:
                descriptor_map = InputDescriptorMapping(
                    _id=desc_id,
                    fmt="ldp_vp",
                    path=f"$.verifiableCredential[{dict_of_creds[tmp_cred.given_id]}]",
                )
                descriptors.append(descriptor_map)

    descriptors = sorted(descriptors, key=lambda i: i._id)
    return (result, descriptors)
