"""Web Requests and Responses schemas."""

from marshmallow import fields, validate
from ..key_type import BLS12381G2, ED25519
from ..did_method import KEY, PEER2, PEER4, SOV
from ...ledger.endpoint_type import EndpointType
from ...vc.vc_di.models import DIProofOptionsSchema
from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import (
    DID_POSTURE_EXAMPLE,
    DID_POSTURE_VALIDATE,
    ENDPOINT_EXAMPLE,
    ENDPOINT_TYPE_EXAMPLE,
    ENDPOINT_TYPE_VALIDATE,
    ENDPOINT_VALIDATE,
    GENERIC_DID_EXAMPLE,
    GENERIC_DID_VALIDATE,
    INDY_DID_EXAMPLE,
    INDY_DID_VALIDATE,
    INDY_RAW_PUBLIC_KEY_EXAMPLE,
    INDY_RAW_PUBLIC_KEY_VALIDATE,
    JWT_EXAMPLE,
    JWT_VALIDATE,
    NON_SD_LIST_EXAMPLE,
    NON_SD_LIST_VALIDATE,
    SD_JWT_EXAMPLE,
    SD_JWT_VALIDATE,
    StrOrDictField,
    Uri,
)


class WalletModuleResponseSchema(OpenAPISchema):
    """Response schema for Wallet Module."""


class DIDSchema(OpenAPISchema):
    """Result schema for a DID."""

    did = fields.Str(
        required=True,
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "DID of interest", "example": GENERIC_DID_EXAMPLE},
    )
    verkey = fields.Str(
        required=True,
        validate=INDY_RAW_PUBLIC_KEY_VALIDATE,
        metadata={
            "description": "Public verification key",
            "example": INDY_RAW_PUBLIC_KEY_EXAMPLE,
        },
    )
    posture = fields.Str(
        required=True,
        validate=DID_POSTURE_VALIDATE,
        metadata={
            "description": (
                "Whether DID is current public DID, posted to ledger but not current"
                " public DID, or local to the wallet"
            ),
            "example": DID_POSTURE_EXAMPLE,
        },
    )
    method = fields.Str(
        required=True,
        metadata={
            "description": "Did method associated with the DID",
            "example": SOV.method_name,
        },
    )
    key_type = fields.Str(
        required=True,
        validate=validate.OneOf([ED25519.key_type, BLS12381G2.key_type]),
        metadata={
            "description": "Key type associated with the DID",
            "example": ED25519.key_type,
        },
    )
    metadata = fields.Dict(
        required=False,
        metadata={"description": "Additional metadata associated with the DID"},
    )


class DIDResultSchema(OpenAPISchema):
    """Result schema for a DID."""

    result = fields.Nested(DIDSchema())


class DIDListSchema(OpenAPISchema):
    """Result schema for connection list."""

    results = fields.List(
        fields.Nested(DIDSchema()), metadata={"description": "DID list"}
    )


class DIDEndpointWithTypeSchema(OpenAPISchema):
    """Request schema to set DID endpoint of particular type."""

    did = fields.Str(
        required=True,
        validate=INDY_DID_VALIDATE,
        metadata={"description": "DID of interest", "example": INDY_DID_EXAMPLE},
    )
    endpoint = fields.Str(
        required=False,
        validate=ENDPOINT_VALIDATE,
        metadata={
            "description": "Endpoint to set (omit to delete)",
            "example": ENDPOINT_EXAMPLE,
        },
    )
    endpoint_type = fields.Str(
        required=False,
        validate=ENDPOINT_TYPE_VALIDATE,
        metadata={
            "description": (
                f"Endpoint type to set (default '{EndpointType.ENDPOINT.w3c}'); affects"
                " only public or posted DIDs"
            ),
            "example": ENDPOINT_TYPE_EXAMPLE,
        },
    )


class JWSCreateSchema(OpenAPISchema):
    """Request schema to create a jws with a particular DID."""

    headers = fields.Dict()
    payload = fields.Dict(required=True)
    did = fields.Str(
        required=False,
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "DID of interest", "example": GENERIC_DID_EXAMPLE},
    )
    verification_method = fields.Str(
        data_key="verificationMethod",
        required=False,
        validate=Uri(),
        metadata={
            "description": "Information used for proof verification",
            "example": (
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg34"
                "2Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ),
        },
    )


class SDJWSCreateSchema(JWSCreateSchema):
    """Request schema to create an sd-jws with a particular DID."""

    non_sd_list = fields.List(
        fields.Str(
            required=False,
            validate=NON_SD_LIST_VALIDATE,
            metadata={"example": NON_SD_LIST_EXAMPLE},
        )
    )


class JWSVerifySchema(OpenAPISchema):
    """Request schema to verify a jws created from a DID."""

    jwt = fields.Str(validate=JWT_VALIDATE, metadata={"example": JWT_EXAMPLE})


class SDJWSVerifySchema(OpenAPISchema):
    """Request schema to verify an sd-jws created from a DID."""

    sd_jwt = fields.Str(validate=SD_JWT_VALIDATE, metadata={"example": SD_JWT_EXAMPLE})


class JWSVerifyResponseSchema(OpenAPISchema):
    """Response schema for JWT verification result."""

    valid = fields.Bool(required=True)
    error = fields.Str(required=False, metadata={"description": "Error text"})
    kid = fields.Str(required=True, metadata={"description": "kid of signer"})
    headers = fields.Dict(
        required=True, metadata={"description": "Headers from verified JWT."}
    )
    payload = fields.Dict(
        required=True, metadata={"description": "Payload from verified JWT"}
    )


class SDJWSVerifyResponseSchema(JWSVerifyResponseSchema):
    """Response schema for SD-JWT verification result."""

    disclosures = fields.List(
        fields.List(StrOrDictField()),
        metadata={
            "description": "Disclosure arrays associated with the SD-JWT",
            "example": [
                ["fx1iT_mETjGiC-JzRARnVg", "name", "Alice"],
                [
                    "n4-t3mlh8jSS6yMIT7QHnA",
                    "street_address",
                    {"_sd": ["kLZrLK7enwfqeOzJ9-Ss88YS3mhjOAEk9lr_ix2Heng"]},
                ],
            ],
        },
    )


class DIDEndpointSchema(OpenAPISchema):
    """Request schema to set DID endpoint; response schema to get DID endpoint."""

    did = fields.Str(
        required=True,
        validate=INDY_DID_VALIDATE,
        metadata={"description": "DID of interest", "example": INDY_DID_EXAMPLE},
    )
    endpoint = fields.Str(
        required=False,
        validate=ENDPOINT_VALIDATE,
        metadata={
            "description": "Endpoint to set (omit to delete)",
            "example": ENDPOINT_EXAMPLE,
        },
    )


class DIDListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for DID list request query string."""

    did = fields.Str(
        required=False,
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "DID of interest", "example": GENERIC_DID_EXAMPLE},
    )
    verkey = fields.Str(
        required=False,
        validate=INDY_RAW_PUBLIC_KEY_VALIDATE,
        metadata={
            "description": "Verification key of interest",
            "example": INDY_RAW_PUBLIC_KEY_EXAMPLE,
        },
    )
    posture = fields.Str(
        required=False,
        validate=DID_POSTURE_VALIDATE,
        metadata={
            "description": (
                "Whether DID is current public DID, posted to ledger but current public"
                " DID, or local to the wallet"
            ),
            "example": DID_POSTURE_EXAMPLE,
        },
    )
    method = fields.Str(
        required=False,
        validate=validate.OneOf(
            [KEY.method_name, SOV.method_name, PEER2.method_name, PEER4.method_name]
        ),
        metadata={
            "example": KEY.method_name,
            "description": (
                "DID method to query for. e.g. sov to only fetch indy/sov DIDs"
            ),
        },
    )
    key_type = fields.Str(
        required=False,
        validate=validate.OneOf([ED25519.key_type, BLS12381G2.key_type]),
        metadata={"example": ED25519.key_type, "description": "Key type to query for."},
    )


class DIDQueryStringSchema(OpenAPISchema):
    """Parameters and validators for set public DID request query string."""

    did = fields.Str(
        required=True,
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "DID of interest", "example": GENERIC_DID_EXAMPLE},
    )


class DIDCreateOptionsSchema(OpenAPISchema):
    """Parameters and validators for create DID options."""

    key_type = fields.Str(
        required=True,
        validate=validate.OneOf([ED25519.key_type, BLS12381G2.key_type]),
        metadata={
            "example": ED25519.key_type,
            "description": (
                "Key type to use for the DID keypair. "
                + "Validated with the chosen DID method's supported key types."
            ),
        },
    )

    did = fields.Str(
        required=False,
        validate=GENERIC_DID_VALIDATE,
        metadata={
            "description": (
                "Specify final value of the did (including did:<method>: prefix)"
                + "if the method supports or requires so."
            ),
            "example": GENERIC_DID_EXAMPLE,
        },
    )


class DIDCreateSchema(OpenAPISchema):
    """Parameters and validators for create DID endpoint."""

    method = fields.Str(
        required=False,
        dump_default=SOV.method_name,
        metadata={
            "example": SOV.method_name,
            "description": (
                "Method for the requested DID."
                + "Supported methods are 'key', 'sov', and any other registered method."
            ),
        },
    )

    options = fields.Nested(
        DIDCreateOptionsSchema,
        required=False,
        metadata={
            "description": (
                "To define a key type and/or a did depending on chosen DID method."
            )
        },
    )

    seed = fields.Str(
        required=False,
        metadata={
            "description": (
                "Optional seed to use for DID, Must be enabled in configuration before"
                " use."
            ),
            "example": "000000000000000000000000Trustee1",
        },
    )


class CreateAttribTxnForEndorserOptionSchema(OpenAPISchema):
    """Class for user to input whether to create a transaction for endorser or not."""

    create_transaction_for_endorser = fields.Boolean(
        required=False,
        metadata={"description": "Create Transaction For Endorser's signature"},
    )


class AttribConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        required=False, metadata={"description": "Connection identifier"}
    )


class MediationIDSchema(OpenAPISchema):
    """Class for user to optionally input a mediation_id."""

    mediation_id = fields.Str(
        required=False, metadata={"description": "Mediation identifier"}
    )


class DISignRequestSchema(OpenAPISchema):
    """Request schema to add a DI proof to a document."""

    document = fields.Dict(
        required=True,
        metadata={"example": 
            {
                "hello": "world"
            }
        }
    )
    options = fields.Nested(
        DIProofOptionsSchema,
        metadata={"example": 
            {
                "type": "DataIntegrityProof",
                "cryptosuite": "eddsa-jcs-2022",
                "proofPurpose": "assertionMethod",
                "verificationMethod": "did:key:z6MktCbksa2qXGqxPNRWni9d7AcaXJKfX48bVXTviL\
                    M32tvQ#z6MktCbksa2qXGqxPNRWni9d7AcaXJKfX48bVXTviLM32tvQ",
            }
        }
    )
    
class DISignResponseSchema(OpenAPISchema):
    """Request schema to add a DI proof to a document."""

    secured_document = fields.Dict(
        required=True,
        metadata={"example": 
            {
                "hello": "world"
            }
        }
    )

class DIVerifyRequestSchema(OpenAPISchema):
    """Request schema to add a DI proof to a document."""

    secured_document = fields.Dict(
        data_key="securedDocument",
        required=True,
        metadata={"example": 
            {
                "hello": "world",
                "proof": [
                {
                    "cryptosuite": "eddsa-jcs-2022",
                    "proofPurpose": "assertionMethod",
                    "type": "DataIntegrityProof",
                    "verificationMethod": "did:key:z6MksxraKwH8GR7NKeQ4HVZAeRKvD76kfd6G7\
                        jm8MscbDmy8#z6MksxraKwH8GR7NKeQ4HVZAeRKvD76kfd6G7jm8MscbDmy8",
                    "proofValue": "zHtda8vV7kJQUPfSKiTGSQDhZfhkgtpnVziT7cdEzhufjPjbeRmys\
                        HvizMJEox1eHR7xUGzNUj1V4yaKiLw7UA6E"
                }
                ]
            }
        }
    )

class DIVerifyResponseSchema(OpenAPISchema):
    """Request schema to add a DI proof to a document."""

    verified = fields.Bool(
        metadata={
            "description": "Verified",
            "example": True
        }
    )