# Anoncreds Proof Validation in ACA-Py

ACA-Py performs pre-validation when verifying Anoncreds presentations (proofs). Some scenarios are rejected (such as those indicative of tampering), while some attributes are removed before running the anoncreds validation (e.g., removing superfluous non-revocation timestamps). Any ACA-Py validations or presentation modifications are indicated by the "verify_msgs" attribute in the final presentation exchange object.

The list of possible verification messages can be found [here](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/indy/verifier.py#L24), and consists of:

```python
class PresVerifyMsg(str, Enum):
    """Credential verification codes."""

    RMV_REFERENT_NON_REVOC_INTERVAL = "RMV_RFNT_NRI"
    RMV_GLOBAL_NON_REVOC_INTERVAL = "RMV_GLB_NRI"
    TSTMP_OUT_NON_REVOC_INTRVAL = "TS_OUT_NRI"
    CT_UNREVEALED_ATTRIBUTES = "UNRVL_ATTR"
    PRES_VALUE_ERROR = "VALUE_ERROR"
    PRES_VERIFY_ERROR = "VERIFY_ERROR"
```

If there is additional information, it will be included like this: `TS_OUT_NRI::19_uuid` (which means the attribute identified by `19_uuid` contained a timestamp outside of the non-revocation interval (this is just a warning)).

A presentation verification may include multiple messages, for example:

```python
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

```python
    ...
    "verified": "false",
    "verified_msgs": [
        "VALUE_ERROR::Encoded representation mismatch for 'Preferred Name'"
    ],
    ...
```

... or the `verified_msgs` may be null or an empty array.

## Presentation Modifications and Warnings

The following modifications/warnings may be made by ACA-Py, which shouldn't affect the verification of the received proof:

- "RMV_RFNT_NRI": Referent contains a non-revocation interval for a non-revocable credential (timestamp is removed)
- "RMV_GLB_NRI": Presentation contains a global interval for a non-revocable credential (timestamp is removed)
- "TS_OUT_NRI": Presentation contains a non-revocation timestamp outside of the requested non-revocation interval (warning)
- "UNRVL_ATTR": Presentation contains attributes with unrevealed values (warning)

## Presentation Pre-validation Errors

The following pre-verification checks are performed, which will cause the proof to fail (before calling anoncreds) and result in the following message:

```plaintext
VALUE_ERROR::<description of the failed validation>
```

These validations are all performed within the [Indy verifier class](https://github.com/hyperledger/aries-cloudagent-python/blob/main/aries_cloudagent/indy/verifier.py) - to see the detailed validation, look for any occurrences of `raise ValueError(...)` in the code.

A summary of the possible errors includes:

- Information missing in presentation exchange record
- Timestamp provided for irrevocable credential
- Referenced revocation registry not found on ledger
- Timestamp outside of reasonable range (future date or pre-dates revocation registry)
- Mismatch between provided and requested timestamps for non-revocation
- Mismatch between requested and provided attributes or predicates
- Self-attested attribute provided for a requested attribute with restrictions
- Encoded value doesn't match raw value

## Anoncreds Verification Exceptions

Typically, when you call the anoncreds `verifier_verify_proof()` method, it will return a `True` or `False` based on whether the presentation cryptographically verifies. However, in the case where anoncreds throws an exception, the exception text will be included in a verification message as follows:

```plaintext
VERIFY_ERROR::<the exception text>
```
