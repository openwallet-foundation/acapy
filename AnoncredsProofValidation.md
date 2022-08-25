# Anoncreds Proof Validation in Aca-Py

Aca-Py does some pre-validation when verifying Anoncreds presentations (proofs), some scenarios are rejected (things that are indicative of tampering, for example) and some attributes are removed before running the anoncreds validation (for example removing superfluous non-revocation timestamps).  Any Aca-Py validations or presentation modifications are indicated by the "verify_msgs" attribute in the final presentation exchange object

The list of possible verification messages is [here](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/indy/verifier.py#L24), and consists of:

```
class PresVerifyMsg(str, Enum):
    """Credential verification codes."""

    RMV_REFERENT_NON_REVOC_INTERVAL = "RMV_RFNT_NRI"
    RMV_GLOBAL_NON_REVOC_INTERVAL = "RMV_GLB_NRI"
    TSTMP_OUT_NON_REVOC_INTRVAL = "TS_OUT_NRI"
    CT_UNREVEALED_ATTRIBUTES = "UNRVL_ATTR"
    PRES_VALUE_ERROR = "VALUE_ERROR"
    PRES_VERIFY_ERROR = "VERIFY_ERROR"
```

If there is additional information, it will be included like this:  `TS_OUT_NRI::19_uuid` (which means the attribute identified by `19_uuid` contained a timestamp outside of the non-revocation interval (which is just a warning)).

A presentation verification may include multiple messages, for example:

```
    ...
    "verified": "true",
    "verified_msgs": [
        "TS_OUT_NRI::18_uuid",
        "TS_OUT_NRI::18_id_GE_uuid",
        "TS_OUT_NRI::18_busid_GE_uuid"
    ],
    ...
```

... or it may include a single message, for example:

```
    ...
    "verified": "false",
    "verified_msgs": [
        "VALUE_ERROR::Encoded representation mismatch for 'Preferred Name'"
    ],
    ...
```

... or the `verified_msgs` may be null or an empty array.

## Presentation Modifications and Warnings

The following modifications/warnings may be done by Aca-Py which shouldn't affect the verification of the received proof):

- "RMV_RFNT_NRI":  Referent contains a non-revocation interval for a non-revocable credential (timestamp is removed)
- "RMV_GLB_NRI":  Presentation contains a global interval for a non-revocable credential (timestamp is removed)
- "TS_OUT_NRI":  Presentation contains a non-revocation timestamp outside of the requested non-revocation interval (warning)
- "UNRVL_ATTR":  Presentation contains attributes with unrevealed values (warning)

## Presentation Pre-validation Errors

The following pre-verification checks are done, which will fail the proof (before calling anoncreds) and will result in the following message:

```
VALUE_ERROR::<description of the failed validation>
```

These validations are all done within the [Indy verifier class](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/indy/verifier.py) - to see the detailed validation just look for anywhere a `raise ValueError(...)` appears in the code.

A summary of the possible errors is:

- information missing in presentation exchange record
- timestamp provided for irrevocable credential
- referenced revocation registry not found on ledger
- timestamp outside of reasonable range (future date or pre-dates revocation registry)
- mis-match between provided and requested timestamps for non-revocation
- mis-match between requested and provided attributes or predicates
- self-attested attribute is provided for a requested attribute with restrictions
- encoded value doesn't match raw value

## Anoncreds Verification Exceptions

Typically when you call the anoncreds `verifier_verify_proof()` method, it will return a `True` or `False` based on whether the presentation cryptographically verifies.  However in the case where anoncreds throws an exception, the exception text will be included in a verification message as follows:

```
VERIFY_ERROR::<the exception text>
```

