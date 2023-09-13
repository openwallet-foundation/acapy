# SD-JWT Implementation in ACA-Py

This document describes the implementation of SD-JWTs in ACA-Py according to the [Selective Disclosure for JWTs (SD-JWT) Specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-selective-disclosure-jwt-05), which defines a mechanism for selective disclosure of individual elements of a JSON object used as the payload of a JSON Web Signature structure.

This implementation adds an important privacy-preserving feature to JWTs, since the receiver of an unencrypted JWT can view all claims within. This feature allows the holder to present only a relevant subset of the claims for a given presentation. The issuer includes plaintext claims, called disclosures, outside of the JWT. Each disclosure corresponds to a hidden claim within the JWT. When a holder prepares a presentation, they include along with the JWT only the disclosures corresponding to the claims they wish to reveal. The verifier verifies that the disclosures in fact correspond to claim values within the issuer-signed JWT. The verifier cannot view the claim values not disclosed by the holder.

In addition, this implementation includes an optional mechanism for key binding, which is the concept of binding an SD-JWT to a holder's public key and requiring that the holder prove possession of the corresponding private key when presenting the SD-JWT.

## Issuer Instructions

The issuer determines which claims in an SD-JWT can be selectively disclosable. In this implementation, all claims at all levels of the JSON structure are by default selectively disclosable. If the issuer wishes for certain claims to always be visible, they can indicate which claims should not be selectively disclosable, as described below. Essential verification data such as `iss`, `iat`, `exp`, and `cnf` are always visible.

The issuer creates a list of JSON paths for the claims that will not be selectively disclosable. Here is an example payload:
```
{
    "birthdate": "1940-01-01",
    "address": {
        "street_address": "123 Main St",
        "locality": "Anytown",
        "region": "Anystate",
        "country": "US",
    },
    "nationalities": ["US", "DE", "SA"],
}

```

| Attribute to access         | JSON path     |
|--------------|-----------|
| "birthdate" | "birthdate"      |
| The country attribute within the address dictionary      | "address.country" |
| The second item in the nationalities list   | "nationalities[1]  |
| All items in the nationalities list  | "nationalities[0:2]"  |

The (specification)[https://datatracker.ietf.org/doc/html/draft-ietf-oauth-selective-disclosure-jwt-05#name-nested-data-in-sd-jwts] defines options for how the issuer can handle nested structures with respect to selective disclosability. As mentioned, all claims at all levels of the JSON structure are by default selectively disclosable.

### [Option 1: Flat SD-JWT](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-selective-disclosure-jwt-05#section-5.7.1)
The issuer can decide to treat the `address` claim in the above example payload as a block that can either be disclosed completely or not at all.

The issuer lists out all the claims inside "address" in the `non_sd_list`, but not `address` itself:
```
non_sd_list = [
    "address.street_address",
    "address.locality",
    "address.region",
    "address.country",
]
```

### [Option 2: Structured SD-JWT](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-selective-disclosure-jwt-05#section-5.7.2)
The issuer may instead decide to make the `address` claim contents selectively disclosable individually.

The issuer lists only "address" in the `non_sd_list`.
```
non_sd_list = ["address"]
```

### [Option 3: SD-JWT with Recursive Disclosures](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-selective-disclosure-jwt-05#section-5.7.3)
The issuer may also decide to make the `address` claim contents selectively disclosable recursively, i.e., the `address` claim is made selectively disclosable as well as its sub-claims.

The issuer lists neither `address` nor the subclaims of `address` in the `non_sd_list`, leaving all with their default selective disclosability. If all claims can be selectively disclosable, the `non_sd_list` need not be defined explicitly.


## Walk-Through of SD-JWT Implementation

### Signing SD-JWTs
THe `sd_jwt_sign` method:
- Creates the list of claims that are selectively disclosable
    - Uses the `non_sd_list` compared against the list of JSON paths for all claims to create the list of JSON paths for selectively disclosable claims
    - Separates list splices if necessary
    - Sorts the `sd_list` so that the claims deepest in the structure are handled first
        - Since we will wrap the selectively disclosable claim keys, the JSON paths for nested structures do not work properly when the claim key is wrapped in an object
- Uses the JSON paths in the `sd_list` to find each selectively disclosable claim and wrap it in the `SDObj` defined by the [sd-jwt Python library](https://github.com/openwallet-foundation-labs/sd-jwt-python) and removes/replaces the original entry
    - For list items, the element itself is wrapped
    - For other objects, the dictionary key is wrapped
- With this modified payload, the `SDJWTIssuerACAPy.issue()` method:
    - Checks if there are selectively disclosable claims at any level in the payload
    - Assembles the SD-JWT payload and creates the disclosures
    - Calls `SDJWTIssuerACAPy._create_signed_jws()`, which is redefined in order to use the ACA-Py `jwt_sign` method and which creates the JWT
    - Combines and returns the signed JWT with its disclosures and option key binding JWT, as indicated in the [specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-selective-disclosure-jwt-05#name-sd-jwt-structure)


### Verifying SD-JWTs
`sd_jwt_verify`:
- Parses the SD-JWT presentation into its component parts: JWT, disclosures, and optional key binding
    - The JWT payload is parsed from its headers and signature
- Creates a list of plaintext disclosures
- Calls `SDJWTVerifierACAPy._verify_sd_jwt`, which is redefined in order to use the ACA-Py `jwt_verify` method, and which returns the verified JWT
- If key binding is used, the key binding JWT is verified and checked against the expected audience and nonce values
