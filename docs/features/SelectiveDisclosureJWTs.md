# SD-JWT Implementation in ACA-Py

This document describes the implementation of SD-JWTs in ACA-Py according to the [Selective Disclosure for JWTs (SD-JWT) Specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-selective-disclosure-jwt-05), which defines a mechanism for selective disclosure of individual elements of a JSON object used as the payload of a JSON Web Signature structure.

This implementation adds an important privacy-preserving feature to JWTs, since the receiver of an unencrypted JWT can view all claims within. This feature allows the holder to present only a relevant subset of the claims for a given presentation. The issuer includes plaintext claims, called disclosures, outside of the JWT. Each disclosure corresponds to a hidden claim within the JWT. When a holder prepares a presentation, they include along with the JWT only the disclosures corresponding to the claims they wish to reveal. The verifier verifies that the disclosures in fact correspond to claim values within the issuer-signed JWT. The verifier cannot view the claim values not disclosed by the holder.

In addition, this implementation includes an optional mechanism for key binding, which is the concept of binding an SD-JWT to a holder's public key and requiring that the holder prove possession of the corresponding private key when presenting the SD-JWT.

## Issuer Instructions

The issuer determines which claims in an SD-JWT can be selectively disclosable. In this implementation, all claims at all levels of the JSON structure are by default selectively disclosable. If the issuer wishes for certain claims to always be visible, they can indicate which claims should not be selectively disclosable, as described below. Essential verification data such as `iss`, `iat`, `exp`, and `cnf` are always visible.

The issuer creates a list of JSON paths for the claims that will not be selectively disclosable. Here is an example payload:

```json
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

| Attribute to access                                 | JSON path            |
| --------------------------------------------------- | -------------------- |
| "birthdate"                                         | "birthdate"          |
| The country attribute within the address dictionary | "address.country"    |
| The second item in the nationalities list           | "nationalities[1]    |
| All items in the nationalities list                 | "nationalities[0:2]" |

The [specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-selective-disclosure-jwt-05#name-nested-data-in-sd-jwts) defines options for how the issuer can handle nested structures with respect to selective disclosability. As mentioned, all claims at all levels of the JSON structure are by default selectively disclosable.

### [Option 1: Flat SD-JWT](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-selective-disclosure-jwt-05#section-5.7.1)

The issuer can decide to treat the `address` claim in the above example payload as a block that can either be disclosed completely or not at all.

The issuer lists out all the claims inside "address" in the `non_sd_list`, but not `address` itself:

```json
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

```json
non_sd_list = ["address"]
```

### [Option 3: SD-JWT with Recursive Disclosures](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-selective-disclosure-jwt-05#section-5.7.3)

The issuer may also decide to make the `address` claim contents selectively disclosable recursively, i.e., the `address` claim is made selectively disclosable as well as its sub-claims.

The issuer lists neither `address` nor the subclaims of `address` in the `non_sd_list`, leaving all with their default selective disclosability. If all claims can be selectively disclosable, the `non_sd_list` need not be defined explicitly.

## Walk-Through of SD-JWT Implementation

### Signing SD-JWTs

#### Example input to `/wallet/sd-jwt/sign` endpoint

```json
{
  "did": "WpVJtxKVwGQdRpQP8iwJZy",
  "headers": {},
  "payload": {
    "sub": "user_42",
    "given_name": "John",
    "family_name": "Doe",
    "email": "johndoe@example.com",
    "phone_number": "+1-202-555-0101",
    "phone_number_verified": true,
    "address": {
      "street_address": "123 Main St",
      "locality": "Anytown",
      "region": "Anystate",
      "country": "US"
    },
    "birthdate": "1940-01-01",
    "updated_at": 1570000000,
    "nationalities": ["US", "DE", "SA"],
    "iss": "https://example.com/issuer",
    "iat": 1683000000,
    "exp": 1883000000
  },
  "non_sd_list": [
    "given_name",
    "family_name",
    "nationalities"
  ]
}

```

#### Output

```bash
"eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJFZERTQSIsICJraWQiOiAiZGlkOnNvdjpXcFZKdHhLVndHUWRScFFQOGl3Slp5I2tleS0xIn0.eyJfc2QiOiBbIkR0a21ha3NkZGtHRjFKeDBDY0kxdmxRTmZMcGFnQWZ1N3p4VnBGRWJXeXciLCAiSlJLb1E0QXVHaU1INWJIanNmNVV4YmJFeDh2YzFHcUtvX0l3TXE3Nl9xbyIsICJNTTh0TlVLNUstR1lWd0swX01kN0k4MzExTTgwVi13Z0hRYWZvRkoxS09JIiwgIlBaM1VDQmdadVRMMDJkV0pxSVY4elUtSWhnalJNX1NTS3dQdTk3MURmLTQiLCAiX294WGNuSW5Yai1SV3BMVHNISU5YaHFrRVAwODkwUFJjNDBISWE1NElJMCIsICJhdnRLVW5Sdnc1clV0TnZfUnAwUll1dUdkR0RzcnJPYWJfVjR1Y05RRWRvIiwgInByRXZJbzBseTVtNTVsRUpTQUdTVzMxWGdVTElOalo5ZkxiRG81U1pCX0UiXSwgImdpdmVuX25hbWUiOiAiSm9obiIsICJmYW1pbHlfbmFtZSI6ICJEb2UiLCAibmF0aW9uYWxpdGllcyI6IFt7Ii4uLiI6ICJPdU1wcEhpYzEySjYzWTBIY2Ffd1BVeDJCTGdUQVdZQjJpdXpMY3lvcU5JIn0sIHsiLi4uIjogIlIxczlaU3NYeVV0T2QyODdEYy1DTVYyMEdvREF3WUVHV3c4ZkVKd1BNMjAifSwgeyIuLi4iOiAid0lJbjdhQlNDVkFZcUF1Rks3Nmpra3FjVGFvb3YzcUhKbzU5WjdKWHpnUSJ9XSwgImlzcyI6ICJodHRwczovL2V4YW1wbGUuY29tL2lzc3VlciIsICJpYXQiOiAxNjgzMDAwMDAwLCAiZXhwIjogMTg4MzAwMDAwMCwgIl9zZF9hbGciOiAic2hhLTI1NiJ9.cIsuGTIPfpRs_Z49nZcn7L6NUgxQumMGQpu8K6rBtv-YRiFyySUgthQI8KZe1xKyn5Wc8zJnRcWbFki2Vzw6Cw~WyJmWURNM1FQcnZicnZ6YlN4elJsUHFnIiwgIlNBIl0~WyI0UGc2SmZ0UnRXdGFPcDNZX2tscmZRIiwgIkRFIl0~WyJBcDh1VHgxbVhlYUgxeTJRRlVjbWV3IiwgIlVTIl0~WyJ4dkRYMDBmalpmZXJpTmlQb2Q1MXFRIiwgInVwZGF0ZWRfYXQiLCAxNTcwMDAwMDAwXQ~WyJYOTlzM19MaXhCY29yX2hudFJFWmNnIiwgInN1YiIsICJ1c2VyXzQyIl0~WyIxODVTak1hM1k3QlFiWUpabVE3U0NRIiwgInBob25lX251bWJlcl92ZXJpZmllZCIsIHRydWVd~WyJRN1FGaUpvZkhLSWZGV0kxZ0Vaal93IiwgInBob25lX251bWJlciIsICIrMS0yMDItNTU1LTAxMDEiXQ~WyJOeWtVcmJYN1BjVE1ubVRkUWVxZXl3IiwgImVtYWlsIiwgImpvaG5kb2VAZXhhbXBsZS5jb20iXQ~WyJlemJwQ2lnVlhrY205RlluVjNQMGJ3IiwgImJpcnRoZGF0ZSIsICIxOTQwLTAxLTAxIl0~WyJvd3ROX3I5Z040MzZKVnJFRWhQU05BIiwgInN0cmVldF9hZGRyZXNzIiwgIjEyMyBNYWluIFN0Il0~WyJLQXktZ0VaWmRiUnNHV1dNVXg5amZnIiwgInJlZ2lvbiIsICJBbnlzdGF0ZSJd~WyJPNnl0anM2SU9HMHpDQktwa0tzU1pBIiwgImxvY2FsaXR5IiwgIkFueXRvd24iXQ~WyI0Nzg5aG5GSjhFNTRsLW91RjRaN1V3IiwgImNvdW50cnkiLCAiVVMiXQ~WyIyaDR3N0FuaDFOOC15ZlpGc2FGVHRBIiwgImFkZHJlc3MiLCB7Il9zZCI6IFsiTXhKRDV5Vm9QQzFIQnhPRmVRa21TQ1E0dVJrYmNrellza1Z5RzVwMXZ5SSIsICJVYkxmVWlpdDJTOFhlX2pYbS15RHBHZXN0ZDNZOGJZczVGaVJpbVBtMHdvIiwgImhsQzJEYVBwT2t0eHZyeUFlN3U2YnBuM09IZ193Qk5heExiS3lPRDVMdkEiLCAia2NkLVJNaC1PaGFZS1FPZ2JaajhmNUppOXNLb2hyYnlhYzNSdXRqcHNNYyJdfV0~"
```

The `sd_jwt_sign()` method:

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

#### Example input to `/wallet/sd-jwt/verify` endpoint

Using the output from the `/wallet/sd-jwt/sign` example above, we have decided to only reveal two of the selectively disclosable claims (`user` and `updated_at`) and achieved this by only including the disclosures for those claims. We have also included a key binding JWT following the disclosures.

```json
{
  "sd_jwt": "eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJFZERTQSIsICJraWQiOiAiZGlkOnNvdjpXcFZKdHhLVndHUWRScFFQOGl3Slp5I2tleS0xIn0.eyJfc2QiOiBbIkR0a21ha3NkZGtHRjFKeDBDY0kxdmxRTmZMcGFnQWZ1N3p4VnBGRWJXeXciLCAiSlJLb1E0QXVHaU1INWJIanNmNVV4YmJFeDh2YzFHcUtvX0l3TXE3Nl9xbyIsICJNTTh0TlVLNUstR1lWd0swX01kN0k4MzExTTgwVi13Z0hRYWZvRkoxS09JIiwgIlBaM1VDQmdadVRMMDJkV0pxSVY4elUtSWhnalJNX1NTS3dQdTk3MURmLTQiLCAiX294WGNuSW5Yai1SV3BMVHNISU5YaHFrRVAwODkwUFJjNDBISWE1NElJMCIsICJhdnRLVW5Sdnc1clV0TnZfUnAwUll1dUdkR0RzcnJPYWJfVjR1Y05RRWRvIiwgInByRXZJbzBseTVtNTVsRUpTQUdTVzMxWGdVTElOalo5ZkxiRG81U1pCX0UiXSwgImdpdmVuX25hbWUiOiAiSm9obiIsICJmYW1pbHlfbmFtZSI6ICJEb2UiLCAibmF0aW9uYWxpdGllcyI6IFt7Ii4uLiI6ICJPdU1wcEhpYzEySjYzWTBIY2Ffd1BVeDJCTGdUQVdZQjJpdXpMY3lvcU5JIn0sIHsiLi4uIjogIlIxczlaU3NYeVV0T2QyODdEYy1DTVYyMEdvREF3WUVHV3c4ZkVKd1BNMjAifSwgeyIuLi4iOiAid0lJbjdhQlNDVkFZcUF1Rks3Nmpra3FjVGFvb3YzcUhKbzU5WjdKWHpnUSJ9XSwgImlzcyI6ICJodHRwczovL2V4YW1wbGUuY29tL2lzc3VlciIsICJpYXQiOiAxNjgzMDAwMDAwLCAiZXhwIjogMTg4MzAwMDAwMCwgIl9zZF9hbGciOiAic2hhLTI1NiJ9.cIsuGTIPfpRs_Z49nZcn7L6NUgxQumMGQpu8K6rBtv-YRiFyySUgthQI8KZe1xKyn5Wc8zJnRcWbFki2Vzw6Cw~WyJ4dkRYMDBmalpmZXJpTmlQb2Q1MXFRIiwgInVwZGF0ZWRfYXQiLCAxNTcwMDAwMDAwXQ~WyJYOTlzM19MaXhCY29yX2hudFJFWmNnIiwgInN1YiIsICJ1c2VyXzQyIl0~eyJhbGciOiAiRWREU0EiLCAidHlwIjogImtiK2p3dCIsICJraWQiOiAiZGlkOnNvdjpXcFZKdHhLVndHUWRScFFQOGl3Slp5I2tleS0xIn0.eyJub25jZSI6ICIxMjM0NTY3ODkwIiwgImF1ZCI6ICJodHRwczovL2V4YW1wbGUuY29tL3ZlcmlmaWVyIiwgImlhdCI6IDE2ODgxNjA0ODN9.i55VeR7bNt7T8HWJcfj6jSLH3Q7vFk8N0t7Tb5FZHKmiHyLrg0IPAuK5uKr3_4SkjuGt1_iNl8Wr3atWBtXMDA"
}
```

#### Verify Output

Note that attributes in the `non_sd_list` (`given_name`, `family_name`, and `nationalities`), as well as essential verification data (`iss`, `iat`, `exp`) are visible directly within the payload. The disclosures include only the values for the `user` and `updated_at` claims, since those are the only selectively disclosable claims that the holder presented. The corresponding hashes for those disclosures appear in the `payload["_sd"]` list.

```json
{
  "headers": {
    "typ": "JWT",
    "alg": "EdDSA",
    "kid": "did:sov:WpVJtxKVwGQdRpQP8iwJZy#key-1"
  },
  "payload": {
    "_sd": [
      "DtkmaksddkGF1Jx0CcI1vlQNfLpagAfu7zxVpFEbWyw",
      "JRKoQ4AuGiMH5bHjsf5UxbbEx8vc1GqKo_IwMq76_qo",
      "MM8tNUK5K-GYVwK0_Md7I8311M80V-wgHQafoFJ1KOI",
      "PZ3UCBgZuTL02dWJqIV8zU-IhgjRM_SSKwPu971Df-4",
      "_oxXcnInXj-RWpLTsHINXhqkEP0890PRc40HIa54II0",
      "avtKUnRvw5rUtNv_Rp0RYuuGdGDsrrOab_V4ucNQEdo",
      "prEvIo0ly5m55lEJSAGSW31XgULINjZ9fLbDo5SZB_E"
    ],
    "given_name": "John",
    "family_name": "Doe",
    "nationalities": [
      {
        "...": "OuMppHic12J63Y0Hca_wPUx2BLgTAWYB2iuzLcyoqNI"
      },
      {
        "...": "R1s9ZSsXyUtOd287Dc-CMV20GoDAwYEGWw8fEJwPM20"
      },
      {
        "...": "wIIn7aBSCVAYqAuFK76jkkqcTaoov3qHJo59Z7JXzgQ"
      }
    ],
    "iss": "https://example.com/issuer",
    "iat": 1683000000,
    "exp": 1883000000,
    "_sd_alg": "sha-256"
  },
  "valid": true,
  "kid": "did:sov:WpVJtxKVwGQdRpQP8iwJZy#key-1",
  "disclosures": [
    [
      "xvDX00fjZferiNiPod51qQ",
      "updated_at",
      1570000000
    ],
    [
      "X99s3_LixBcor_hntREZcg",
      "sub",
      "user_42"
    ]
  ]
}
```

The `sd_jwt_verify()` method:

- Parses the SD-JWT presentation into its component parts: JWT, disclosures, and optional key binding
  - The JWT payload is parsed from its headers and signature
- Creates a list of plaintext disclosures
- Calls `SDJWTVerifierACAPy._verify_sd_jwt`, which is redefined in order to use the ACA-Py `jwt_verify` method, and which returns the verified JWT
- If key binding is used, the key binding JWT is verified and checked against the expected audience and nonce values
