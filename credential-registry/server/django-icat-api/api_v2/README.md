# TOB API V2

## Data Model

The relavant tables in the database related to issuer registration and credential issuance are as follows:

![TheOrgBook Schema Diagram](./docs/images/tob.png)

## Populating the Database

The application's database is populated when issuers register themselves and when an issuer issues a claim to TheOrgBook.

The follow tables are populated when an issuer registers itself:

- issuer
- schema
- credential_type

The following tables are populated when a credential is issued:

- topic
- credential
- claim
- address
- contact
- name
- person

Issuers have no control over the creation of `topic`, `credential`, and `claim` records being created. They are created with every credential implicitly.

`address`, `contact`, `name`, and `person` records are created only if the issuer sends a `mapping` in the issuer registration which we will cover in the next section.

## Issuer Registration

Issuers must register themselves with TheOrgBook before they can begin issuing credentials. The following is an example registration payload:

```json
{
  "issuer": {
    "did": "6qnvgJtqwK44D8LFYnV5Yf", // required
    "name": "BC Corporate Registry", // required
    "abbreviation": "BCReg",
    "email": "bcreg.test.issuer@example.ca",
    "url": "http://localhost:5000"
  },
  "credential_types": [
    {
      "name": "Incorporation",
      "schema": "incorporation.bc_registries",
      "version": "1.0.31",
      "endpoint": "http://localhost:5000/bcreg/incorporation",
      "topic": {
        "source_id": {
          "input": "corp_num",
          "from": "claim"
        },
        "type": {
          "input": "incorporation",
          "from": "value"
        }
      },
      "mapping": [
        {
          "model": "name",
          "fields": {
            "text": {
              "input": "legal_name",
              "from": "claim"
            },
            "type": {
              "input": "legal_name",
              "from": "value"
            }
          }
        }
      ]
    },
    {
      "name": "Doing Business As",
      "schema": "doing_business_as.bc_registries",
      "version": "1.0.31",
      "endpoint": "http://localhost:5000/bcreg/dba",
      "topic": {
        "parent_source_id": {
          "input": "org_registry_id",
          "from": "claim"
        },
        "parent_type": {
          "input": "incorporation",
          "from": "value"
        },
        "source_id": {
          "input": "dba_corp_num",
          "from": "claim"
        },
        "type": {
          "input": "doing_business_as",
          "from": "value"
        }
      },
      "mapping": [
        {
          "model": "name",
          "fields": {
            "text": {
              "input": "dba_name",
              "from": "claim"
            },
            "type": {
              "input": "dba_name",
              "from": "value"
            }
          }
        }
      ]
    },
    {
      "name": "Corporate Address",
      "schema": "address.bc_registries",
      "version": "1.0.31",
      "endpoint": "http://localhost:5000/bcreg/address",
      "topic": [
        {
          "parent_source_id": {
            "input": "org_registry_id",
            "from": "claim"
          },
          "parent_type": {
            "input": "incorporation",
            "from": "value"
          },
          "source_id": {
            "input": "dba_corp_num",
            "from": "claim"
          },
          "type": {
            "input": "doing_business_as",
            "from": "value"
          }
        },
        {
          "source_id": {
            "input": "org_registry_id",
            "from": "claim"
          },
          "type": {
            "input": "incorporation",
            "from": "value"
          }
        }
      ],
      "cardinality_fields": ["addr_type"],
      "mapping": [
        {
          "model": "address",
          "fields": {
            "addressee": {
              "input": "addressee",
              "from": "claim"
            },
            "civic_address": {
              "input": "local_address",
              "from": "claim"
            },
            "city": {
              "input": "municipality",
              "from": "claim"
            },
            "province": {
              "input": "province",
              "from": "claim"
            },
            "postal_code": {
              "input": "postal_code",
              "from": "claim",
              "processor": ["string_helpers.uppercase"]
            },
            "country": {
              "input": "country",
              "from": "claim"
            },
            "type": {
              "input": "addr_type",
              "from": "claim"
            },
            "end_date": {
              "input": "end_date",
              "from": "claim"
            }
          }
        }
      ]
    }
  ]
}
```

`issuer` provides information about the issuer. If a new registration is sent by the issuer, TheOrgBook will retrieve an existing record by `did` and update the relevant issuer record. At a minimum, the issuer must send `did` and `name`.

`credential_types` specifies the types of credentials that TheOrgBook will process from the issuer. `name`, `schema`, `version`, and `topic` are required. `name` is used for display purposes. `schema` and `version` must be valid schema name and version from the Indy ledger. `topic` is used to determine which _topic_ each credential is related to. More on this later.

`mapping` is optional and allows issuers to populate the following tables:

- address
- contact
- name
- person

These tables are used to power the UI as well as the public API. It is the issuer's responsibility to use this mechanism if it wants its data to be searchable in TheOrgBook.

## Creating a mapping

Take the following `credential_type` for example:

```json
{
  "name": "Corporate Address",
  "schema": "address.bc_registries",
  "version": "1.0.31",
  "endpoint": "http://localhost:5000/bcreg/address",
  "topic": [
    {
      "parent_source_id": {
        "input": "org_registry_id",
        "from": "claim"
      },
      "parent_type": {
        "input": "incorporation",
        "from": "value"
      },
      "source_id": {
        "input": "dba_corp_num",
        "from": "claim"
      },
      "type": {
        "input": "doing_business_as",
        "from": "value"
      }
    },
    {
      "source_id": {
        "input": "org_registry_id",
        "from": "claim"
      },
      "type": {
        "input": "incorporation",
        "from": "value"
      }
    }
  ],
  "cardinality_fields": ["addr_type"],
  "mapping": [
    {
      "model": "address",
      "fields": {
        "addressee": {
          "input": "addressee",
          "from": "claim"
        },
        "civic_address": {
          "input": "local_address",
          "from": "claim"
        },
        "city": {
          "input": "municipality",
          "from": "claim"
        },
        "province": {
          "input": "province",
          "from": "claim"
        },
        "postal_code": {
          "input": "postal_code",
          "from": "claim",
          "processor": ["string_helpers.uppercase"]
        },
        "country": {
          "input": "country",
          "from": "claim"
        },
        "type": {
          "input": "addr_type",
          "from": "claim"
        },
        "end_date": {
          "input": "end_date",
          "from": "claim"
        }
      }
    }
  ]
}
```

This `credential_type` represents a type of credential that TheOrgBook should be aware of. A credential roughly maps to a _credential definition_ in Indy terms.

### Cardinality Fields

The key `cardinality_fields` is optional. By setting `cardinality_fields` an issuer can instruct TheOrgBook to loosen the rules it uses to apply an end_date to an existing credential to indicate that it is historical (expired). By default, TheOrgBook will find any credential of this `credential_type` and `topic` with `end_date` null and set an end date before creating a new credential. In the example above, we also take into account the value in claim `addr_type` to restrict the search for existing credential. This means that each topic can have multiple 'address' credentials – one of each `addr_type`.

### Selecting a Topic

In order to populate TheOrgBook's search database, first a _topic selector_ must be defined. A _topic_ represents many credentials and related search models. Every credential must provide enough information to select a topic and an optional parent topic. If the selection of a topic varies based on the content of the credential, an issuer can submit an array of topic selectors in order of decreasing priority.

In the above example, TheOrgBook will first attempt to select a topic of `type` 'doing*business_as' with `source_id` being the value in claim 'dba_corp_num' as well as a parent topic with related claims. If the credential does not contain a value for claim 'dba_corp_num', it will fall back to the next topic selector in the array. In the latter case, a parent topic is not specified indicating that this credential is related to a \_root* topic.

Each topic selector has the following format:

```json
{
  "parent_source_id": <credential_mapper>,
  "parent_type": <credential_mapper>,
  "source_id": <credential_mapper>,
  "type": <credential_mapper>
}
```

See below for the credential_mapper syntax.

### Creating search models

Each `mapping` requires a `model` key. This key is used to identify the model it wishes to populate from incoming claims. The acceptable values are `address`, `contact`, `name`, and `person`.

The fields key represents the fields on each model that can be populated from claim data. The available fields on each model are as follows:

| _address_     |
| ------------- |
| addressee     |
| civic_address |
| city          |
| province      |
| postal_code   |
| country       |
| type          |

| _name_   |
| -------- |
| text     |
| language |

| _person_  |
| --------- |
| full_name |

| _contact_ |
| --------- |
| text      |
| type      |

Each field can be populated using a `credential_mapper` (see below).

### Credential Mapper

A `credential_mapper` has the following format:

```json
{
  "input": <string>, //required
  "from": <string>, //required
  "processor": <array<string>> //optional
}
```

A credential mapper must have an `input` and a `from` key. If `from` is set to 'value', then the value of that field on that model will always be set to the string literal provided in `input`. If `from` is set to 'claim', then it will retrieve the value of the claim on each each incoming credential. `processor` allows you to run the resulting value from either of the two cases through a series of functions. The input of each function is the output of the last. If you need to add new functions to be made available to the processor, you can make a pull request to TheOrgBook. See more information [here](./processor).
