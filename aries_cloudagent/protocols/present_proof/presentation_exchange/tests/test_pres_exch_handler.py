import json
import pytest

from asynctest import mock as async_mock
from asynctest import TestCase as AsyncTestCase
from copy import deepcopy
from time import time
from unittest import TestCase
from uuid import uuid4


from .....storage.vc_holder.vc_record import VCRecord

from ..pres_exch import (
    PresentationDefinition,
    Requirement,
    Filter,
    SchemaInputDescriptor,
)
from ..pres_exch_handler import (
    to_requirement,
    make_requirement,
    is_len_applicable,
    exclusive_maximum_check,
    exclusive_minimum_check,
    minimum_check,
    maximum_check,
    length_check,
    pattern_check,
    subject_is_issuer,
    filter_schema,
    credential_match_schema,
    is_numeric,
    merge_nested_results,
    create_vp,
    PresentationExchError,
)

from .test_data import get_test_data


(cred_list, pd_list) = get_test_data()


class TestPresExchEndToEnd(AsyncTestCase):
    """Presentation predicate specification tests"""

    @pytest.mark.asyncio
    async def test_load_cred_json(self):
        """Test deserialization."""
        assert len(cred_list) == 6
        for tmp_pd in pd_list:
            # tmp_pd is tuple of presentation_definition and expected number of VCs
            tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd[0])
            assert len(tmp_vp.credentials) == tmp_pd[1]


class TestPresExchRequirement(AsyncTestCase):
    """Presentation Exchange Requirment tests"""

    async def test_to_requirement_catch_errors(self):
        """Test deserialization."""

        test_json_pd = """
            {
                "submission_requirements": [
                    {
                        "name": "Banking Information",
                        "purpose": "We need you to prove you currently hold a bank account older than 12months.",
                        "rule": "pick",
                        "count": 1,
                        "from": "A"
                    }
                ],
                "id": "32f54163-7166-48f1-93d8-ff217bdb0653",
                "input_descriptors": [
                    {
                        "id": "banking_input_1",
                        "name": "Bank Account Information",
                        "purpose": "We can only remit payment to a currently-valid bank account.",
                        "group": [
                            "B"
                        ],
                        "schema": [
                            {
                                "uri": "https://bank-schemas.org/1.0.0/accounts.json"
                            },
                            {
                                "uri": "https://bank-schemas.org/2.0.0/accounts.json"
                            }
                        ],
                        "constraints": {
                            "fields": [
                                {
                                    "path": [
                                        "$.issuer",
                                        "$.vc.issuer",
                                        "$.iss"
                                    ],
                                    "purpose": "We can only verify bank accounts if they are attested by a trusted bank, auditor or regulatory authority.",
                                    "filter": {
                                        "type": "string",
                                        "pattern": "did:example:123|did:example:456"
                                    }
                                },
                                {
                                    "path": [
                                        "$.credentialSubject.account[*].route",
                                        "$.vc.credentialSubject.account[*].route",
                                        "$.account[*].route"
                                    ],
                                    "purpose": "We can only remit payment to a currently-valid account at a US, Japanese, or German federally-accredited bank, submitted as an ABA RTN or SWIFT code.",
                                    "filter": {
                                        "type": "string",
                                        "pattern": "^[0-9]{9}|^([a-zA-Z]){4}([a-zA-Z]){2}([0-9a-zA-Z]){2}([0-9a-zA-Z]{3})?$"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        with self.assertRaises(PresentationExchError) as cm:
            test_pd = PresentationDefinition.deserialize(test_json_pd)
            await make_requirement(
                srs=test_pd.submission_requirements,
                descriptors=test_pd.input_descriptors,
            )
            assert (
                "Error creating requirement inside to_requirement function"
                in cm.exception
            )

        test_json_pd_nested_srs = """
            {
                "submission_requirements": [
                    {
                        "name": "Citizenship Information",
                        "rule": "pick",
                        "max": 3,
                        "from_nested": [
                            {
                                "name": "United States Citizenship Proofs",
                                "purpose": "We need you to prove your US citizenship.",
                                "rule": "all",
                                "from": "C"
                            },
                            {
                                "name": "European Union Citizenship Proofs",
                                "purpose": "We need you to prove you are a citizen of an EU member state.",
                                "rule": "all",
                                "from": "D"
                            }
                        ]
                    }
                ],
                "id": "32f54163-7166-48f1-93d8-ff217bdb0653",
                "input_descriptors": [
                    {
                        "id": "banking_input_1",
                        "name": "Bank Account Information",
                        "purpose": "We can only remit payment to a currently-valid bank account.",
                        "group": [
                            "B"
                        ],
                        "schema": [
                            {
                                "uri": "https://bank-schemas.org/1.0.0/accounts.json"
                            },
                            {
                                "uri": "https://bank-schemas.org/2.0.0/accounts.json"
                            }
                        ],
                        "constraints": {
                            "fields": [
                                {
                                    "path": [
                                        "$.issuer",
                                        "$.vc.issuer",
                                        "$.iss"
                                    ],
                                    "purpose": "We can only verify bank accounts if they are attested by a trusted bank, auditor or regulatory authority.",
                                    "filter": {
                                        "type": "string",
                                        "pattern": "did:example:123|did:example:456"
                                    }
                                },
                                {
                                    "path": [
                                        "$.credentialSubject.account[*].route",
                                        "$.vc.credentialSubject.account[*].route",
                                        "$.account[*].route"
                                    ],
                                    "purpose": "We can only remit payment to a currently-valid account at a US, Japanese, or German federally-accredited bank, submitted as an ABA RTN or SWIFT code.",
                                    "filter": {
                                        "type": "string",
                                        "pattern": "^[0-9]{9}|^([a-zA-Z]){4}([a-zA-Z]){2}([0-9a-zA-Z]){2}([0-9a-zA-Z]{3})?$"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        with self.assertRaises(PresentationExchError) as cm:
            test_pd = PresentationDefinition.deserialize(test_json_pd_nested_srs)
            await make_requirement(
                srs=test_pd.submission_requirements,
                descriptors=test_pd.input_descriptors,
            )
            assert (
                "Error creating requirement from nested submission_requirements"
                in cm.exception
            )

    async def test_make_requirement_with_none_params(self):
        """Test deserialization."""

        test_json_pd_no_sr = """
            {
                "id": "32f54163-7166-48f1-93d8-ff217bdb0653",
                "input_descriptors": [
                    {
                        "id": "banking_input_1",
                        "name": "Bank Account Information",
                        "purpose": "We can only remit payment to a currently-valid bank account.",
                        "group": [
                            "B"
                        ],
                        "schema": [
                            {
                                "uri": "https://bank-schemas.org/1.0.0/accounts.json"
                            },
                            {
                                "uri": "https://bank-schemas.org/2.0.0/accounts.json"
                            }
                        ],
                        "constraints": {
                            "fields": [
                                {
                                    "path": [
                                        "$.issuer",
                                        "$.vc.issuer",
                                        "$.iss"
                                    ],
                                    "purpose": "We can only verify bank accounts if they are attested by a trusted bank, auditor or regulatory authority.",
                                    "filter": {
                                        "type": "string",
                                        "pattern": "did:example:123|did:example:456"
                                    }
                                },
                                {
                                    "path": [
                                        "$.credentialSubject.account[*].route",
                                        "$.vc.credentialSubject.account[*].route",
                                        "$.account[*].route"
                                    ],
                                    "purpose": "We can only remit payment to a currently-valid account at a US, Japanese, or German federally-accredited bank, submitted as an ABA RTN or SWIFT code.",
                                    "filter": {
                                        "type": "string",
                                        "pattern": "^[0-9]{9}|^([a-zA-Z]){4}([a-zA-Z]){2}([0-9a-zA-Z]){2}([0-9a-zA-Z]{3})?$"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        test_pd = PresentationDefinition.deserialize(test_json_pd_no_sr)
        assert test_pd.submission_requirements is None
        await make_requirement(
            srs=test_pd.submission_requirements, descriptors=test_pd.input_descriptors
        )

        test_json_pd_no_input_desc = """
            {
                "submission_requirements": [
                    {
                        "name": "Banking Information",
                        "purpose": "We need you to prove you currently hold a bank account older than 12months.",
                        "rule": "pick",
                        "count": 1,
                        "from": "A"
                    }
                ],
                "id": "32f54163-7166-48f1-93d8-ff217bdb0653"
            }
        """

        with self.assertRaises(PresentationExchError) as cm:
            test_pd = PresentationDefinition.deserialize(test_json_pd_no_input_desc)
            await make_requirement(
                srs=test_pd.submission_requirements,
                descriptors=test_pd.input_descriptors,
            )


class TestPresExchConstraint(AsyncTestCase):
    """Presentation predicate specification tests"""

    @pytest.mark.asyncio
    async def test_subject_is_issuer_check(self):
        """Test deserialization."""
        test_pd = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                    "name": "Citizenship Information",
                    "rule": "pick",
                    "min": 1,
                    "from": "A"
                    },
                    {
                    "name": "European Union Citizenship Proofs",
                    "rule": "all",
                    "from": "B"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                            "uri":"https://eu.com/claims/DriversLicense.json"
                            }
                        ],
                        "constraints":{
                            "subject_is_issuer": "required",
                            "fields":[
                                {
                                    "path":[
                                        "$.issuer",
                                        "$.vc.issuer",
                                        "$.iss"
                                    ],
                                    "purpose":"The claim must be from one of the specified issuers",
                                    "filter":{
                                        "type":"string",
                                        "enum": ["https://example.edu/issuers/565049", "https://example.edu/issuers/565050", "https://example.edu/issuers/565051", "did:foo:123"]
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "id":"citizenship_input_2",
                        "name":"US Passport",
                        "group":[
                            "B"
                        ],
                        "schema":[
                            {
                            "uri":"https://eu.com/claims/DriversLicense.json"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.credentialSubject.dob",
                                        "$.vc.credentialSubject.dob",
                                        "$.credentialSubject.license.dob"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "format":"date",
                                        "maximum":"1999-5-16"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_vp = await create_vp(
            credentials=cred_list, pd=PresentationDefinition.deserialize(test_pd)
        )


class TestPresExchField(AsyncTestCase):
    """Presentation predicate specification tests"""

    @pytest.mark.asyncio
    async def test_predicate_required_check(self):
        """Test deserialization."""
        test_pd = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                    "name": "Citizenship Information",
                    "rule": "pick",
                    "min": 1,
                    "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                            "uri":"https://eu.com/claims/DriversLicense.json"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.issuer",
                                        "$.vc.issuer",
                                        "$.iss"
                                    ],
                                    "predicate": "required",
                                    "purpose":"The claim must be from one of the specified issuers",
                                    "filter":{
                                        "type":"string",
                                        "enum": ["https://example.edu/issuers/565049", "https://example.edu/issuers/565050", "https://example.edu/issuers/565051", "did:foo:123"]
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        with self.assertRaises(PresentationExchError) as cm:
            tmp_pd = PresentationDefinition.deserialize(test_pd)
            assert (
                tmp_pd.input_descriptors[0].constraint._fields[0].predicate
                == "required"
            )
            tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
            assert "Not yet implemented - createNewCredential" in cm.exception


class TestPresExchFilter(AsyncTestCase):
    """Presentation predicate specification tests"""

    @pytest.mark.asyncio
    async def test_filter_number_type_check(self):
        """Test deserialization."""
        test_pd_min = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                        "uri":"https://eu.com/claims/DriversLicense.json"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "minimum": 2
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_min)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 2

        test_pd_max = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                        "uri":"https://eu.com/claims/DriversLicense.json"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "maximum": 2
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_max)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 2

        test_pd_excl_min = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                        "uri":"https://eu.com/claims/DriversLicense.json"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "exclusiveMinimum": 1.5
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_excl_min)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 2

        test_pd_excl_max = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                        "uri":"https://eu.com/claims/DriversLicense.json"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "exclusiveMaximum": 2.5
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_excl_max)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 2

        test_pd_const = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                        "uri":"https://eu.com/claims/DriversLicense.json"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "const": 2
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_const)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 2

        test_pd_enum = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                        "uri":"https://eu.com/claims/DriversLicense.json"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "enum": [2, 2.0 , "test"]
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_enum)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 2

        test_pd_missing = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                        "uri":"https://eu.com/claims/DriversLicense.json"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number"
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_missing)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 0

    @pytest.mark.asyncio
    async def test_filter_no_type_check(self):
        """Test deserialization."""
        test_pd = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                        "uri":"https://eu.com/claims/DriversLicense.json"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "not": {
                                        "const": 1.5
                                    }
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 2

    @pytest.mark.asyncio
    async def test_filter_string(self):
        """Test deserialization."""
        test_pd_min_length = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                            "uri":"https://eu.com/claims/DriversLicense.json"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.vc.issuer",
                                        "$.issuer",
                                        "$.iss"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "minLength": 5
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_min_length)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 6

        test_pd_max_length = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                            "uri":"https://eu.com/claims/DriversLicense.json"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.issuer",
                                        "$.vc.issuer",
                                        "$.iss"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "maxLength": 20
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_max_length)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 3

        test_pd_pattern_check = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                            "uri":"https://eu.com/claims/DriversLicense.json"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.vc.issuer",
                                        "$.issuer",
                                        "$.iss"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "pattern": "did:example:123|did:foo:123"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_pattern_check)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 3

        test_pd_datetime_exclmax = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                            "uri":"https://eu.com/claims/DriversLicense.json"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.credentialSubject.dob",
                                        "$.vc.credentialSubject.dob",
                                        "$.credentialSubject.license.dob"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "format":"date",
                                        "exclusiveMaximum":"1981-5-16"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_datetime_exclmax)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 2

        test_pd_datetime_exclmin = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                            "uri":"https://eu.com/claims/DriversLicense.json"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.credentialSubject.dob",
                                        "$.vc.credentialSubject.dob",
                                        "$.credentialSubject.license.dob"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "format":"date",
                                        "exclusiveMinimum":"1979-5-16"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_datetime_exclmin)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 2

        test_pd_const_check = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                            "uri":"https://eu.com/claims/DriversLicense.json"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.vc.issuer",
                                        "$.issuer",
                                        "$.iss"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "const": "did:foo:123"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_const_check)
        tmp_vp = await create_vp(credentials=cred_list, pd=tmp_pd)
        assert len(tmp_vp.credentials) == 2

    @pytest.mark.asyncio
    async def test_filter_schema(self):
        tmp_schema_list = [
            SchemaInputDescriptor(
                uri="test123",
                required=True,
            )
        ]
        assert len(await filter_schema(cred_list, tmp_schema_list)) == 0

    @pytest.mark.asyncio
    async def test_cred_schema_match(self):
        tmp_cred = deepcopy(cred_list[0])
        tmp_cred.types = ["test1", "test2"]
        tmp_cred.schema_ids = ["test3"]
        assert await credential_match_schema(tmp_cred, "test2") is True

    @pytest.mark.asyncio
    async def test_merge_nested(self):
        test_nested_result = []
        test_dict_1 = {}
        test_dict_1["citizenship_input_1"] = [
            cred_list[0],
            cred_list[1],
            cred_list[2],
            cred_list[3],
            cred_list[4],
            cred_list[5],
        ]
        test_dict_2 = {}
        test_dict_2["citizenship_input_2"] = [
            cred_list[4],
            cred_list[5],
        ]
        test_dict_3 = {}
        test_dict_3["citizenship_input_2"] = [
            cred_list[3],
            cred_list[2],
        ]
        test_nested_result.append(test_dict_1)
        test_nested_result.append(test_dict_2)
        test_nested_result.append(test_dict_3)

        tmp_result = await merge_nested_results(test_nested_result, {})

    @pytest.mark.asyncio
    async def test_subject_is_issuer(self):
        tmp_cred = deepcopy(cred_list[0])
        tmp_cred.issuer_id = "4fc82e63-f897-4dad-99cc-f698dff6c425"
        tmp_cred.subject_ids.add("4fc82e63-f897-4dad-99cc-f698dff6c425")
        assert tmp_cred.subject_ids is not None
        assert await subject_is_issuer(tmp_cred) is True
        tmp_cred.issuer_id = "19b823fb-55ef-49f4-8caf-2a26b8b9286f"
        assert await subject_is_issuer(tmp_cred) is False


class UtilityTests(TestCase):
    def test_is_numeric(self):
        assert is_numeric("test") is False
        assert is_numeric(1) is True
        assert is_numeric(2 + 3j) is False

    def test_filter_no_match(self):
        tmp_filter_excl_min = Filter(exclusive_min=7)
        assert exclusive_minimum_check("test", tmp_filter_excl_min) is False
        tmp_filter_excl_max = Filter(exclusive_max=10)
        assert exclusive_maximum_check("test", tmp_filter_excl_max) is False
        tmp_filter_min = Filter(minimum=10)
        assert minimum_check("test", tmp_filter_min) is False
        tmp_filter_max = Filter(maximum=10)
        assert maximum_check("test", tmp_filter_max) is False

    def test_filter_valueerror(self):
        tmp_filter_excl_min = Filter(exclusive_min=7, fmt="date")
        assert exclusive_minimum_check("test", tmp_filter_excl_min) is False
        tmp_filter_excl_max = Filter(exclusive_max=10, fmt="date")
        assert exclusive_maximum_check("test", tmp_filter_excl_max) is False
        tmp_filter_min = Filter(minimum=10, fmt="date")
        assert minimum_check("test", tmp_filter_min) is False
        tmp_filter_max = Filter(maximum=10, fmt="date")
        assert maximum_check("test", tmp_filter_max) is False

    def test_filter_length_check(self):
        tmp_filter_both = Filter(min_length=7, max_length=10)
        assert length_check("test12345", tmp_filter_both) is True
        tmp_filter_min = Filter(min_length=7)
        assert length_check("test123", tmp_filter_min) is True
        tmp_filter_max = Filter(max_length=10)
        assert length_check("test", tmp_filter_max) is True
        assert length_check("test12", tmp_filter_min) is False

    def test_filter_pattern_check(self):
        tmp_filter = Filter(pattern="test1|test2")
        assert pattern_check("test3", tmp_filter) is False
        tmp_filter = Filter(const="test3")
        assert pattern_check("test3", tmp_filter) is False

    def test_is_len_applicable(self):
        tmp_req_a = Requirement(count=1)
        tmp_req_b = Requirement(minimum=3)
        tmp_req_c = Requirement(maximum=5)

        assert is_len_applicable(tmp_req_a, 2) is False
        assert is_len_applicable(tmp_req_b, 2) is False
        assert is_len_applicable(tmp_req_c, 6) is False
