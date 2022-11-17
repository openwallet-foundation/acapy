
# Acme Controller Workshop

In this workshop we will add some functionality to a third participant in the Alice/Faber drama - namely, Acme Inc.  After completing her education at Faber College, Alice is going to apply for a job at Acme Inc.  To do this she must provide proof of education (once she has completed the interview and other non-Indy tasks), and then Acme will issue her an employment credential.

Note that an updated Acme controller is available here: https://github.com/ianco/aries-cloudagent-python/tree/acme_workshop/demo if you just want to skip ahead ...  There is also an alternate solution with some additional functionality available here:  https://github.com/ianco/aries-cloudagent-python/tree/agent_workshop/demo


## Preview of the Acme Controller

There is already a skeleton of the Acme controller in place, you can run it as follows.  (Note that beyond establishing a connection it doesn't actually do anything yet.)

To run the Acme controller template, first run Alice and Faber so that Alice can prove her education experience:

Open 2 bash shells, and in each run:

```bash
git clone https://github.com/hyperledger/aries-cloudagent-python.git
cd aries-cloudagent-python/demo
```

In one shell run Faber:

```bash
LEDGER_URL=http://dev.greenlight.bcovrin.vonx.io ./run_demo faber
```

... and in the second shell run Alice:

```bash
LEDGER_URL=http://dev.greenlight.bcovrin.vonx.io ./run_demo alice
```

When Faber has produced an invitation, copy it over to Alice.

Then, in the Faber shell, select option ```1``` to issue a credential to Alice.  (You can select option ```2``` if you like, to confirm via proof.)

Then, in the Faber shell, enter ```X``` to exit the controller, and then run the Acme controller:

```bash
LEDGER_URL=http://dev.greenlight.bcovrin.vonx.io ./run_demo acme
```

In the Alice shell, select option ```4``` (to enter a new invitation) and then copy over Acme's invitation once it's available.

Then, in the Acme shell, you can select option ```2``` and then option ```1```, which don't do anything ... yet!!!


## Asking Alice for a Proof of Education

In the Acme code ```acme.py``` we are going to add code to issue a proof request to Alice, and then validate the received proof.

First the following import statements and constants that we will need near the top of acme.py:

``` python
import random

from datetime import date
from uuid import uuid4
```

``` python
TAILS_FILE_COUNT = int(os.getenv("TAILS_FILE_COUNT", 100))
CRED_PREVIEW_TYPE = "https://didcomm.org/issue-credential/2.0/credential-preview"
```

Next locate the code that is triggered by option ```2```:

``` python
            elif option == "2":
                log_status("#20 Request proof of degree from alice")
                # TODO presentation requests
```

Replace the ```# TODO``` comment with the following code:

``` python
                req_attrs = [
                    {
                        "name": "name",
                        "restrictions": [{"schema_name": "degree schema"}]
                    },
                    {
                        "name": "date",
                        "restrictions": [{"schema_name": "degree schema"}]
                    },
                    {
                        "name": "degree",
                        "restrictions": [{"schema_name": "degree schema"}]
                    }
                ]
                req_preds = []
                indy_proof_request = {
                    "name": "Proof of Education",
                    "version": "1.0",
                    "nonce": str(uuid4().int),
                    "requested_attributes": {
                        f"0_{req_attr['name']}_uuid": req_attr
                        for req_attr in req_attrs
                    },
                    "requested_predicates": {}
                }
                proof_request_web_request = {
                    "connection_id": agent.connection_id,
                    "presentation_request": {"indy": indy_proof_request},
                }
                # this sends the request to our agent, which forwards it to Alice
                # (based on the connection_id)
                await agent.admin_POST(
                    "/present-proof-2.0/send-request",
                    proof_request_web_request
                )
```

Now we need to handle receipt of the proof.  Locate the code that handles received proofs (this is in a webhook callback):

``` python
        if state == "presentation-received":
            # TODO handle received presentations
            pass
```

then replace the ```# TODO``` comment and the ```pass``` statement:

``` python
            log_status("#27 Process the proof provided by X")
            log_status("#28 Check if proof is valid")
            proof = await self.admin_POST(
                f"/present-proof-2.0/records/{pres_ex_id}/verify-presentation"
            )
            self.log("Proof = ", proof["verified"])

            # if presentation is a degree schema (proof of education),
            # check values received
            pres_req = message["by_format"]["pres_request"]["indy"]
            pres = message["by_format"]["pres"]["indy"]
            is_proof_of_education = (
                pres_req["name"] == "Proof of Education"
            )
            if is_proof_of_education:
                log_status("#28.1 Received proof of education, check claims")
                for (referent, attr_spec) in pres_req["requested_attributes"].items():
                    if referent in pres['requested_proof']['revealed_attrs']:
                        self.log(
                            f"{attr_spec['name']}: "
                            f"{pres['requested_proof']['revealed_attrs'][referent]['raw']}"
                        )
                    else:
                        self.log(
                            f"{attr_spec['name']}: "
                            "(attribute not revealed)"
                        )
                for id_spec in pres["identifiers"]:
                    # just print out the schema/cred def id's of presented claims
                    self.log(f"schema_id: {id_spec['schema_id']}")
                    self.log(f"cred_def_id {id_spec['cred_def_id']}")
                # TODO placeholder for the next step
            else:
                # in case there are any other kinds of proofs received
                self.log("#28.1 Received ", pres_req["name"])
```

Right now this just verifies the proof received and prints out the attributes it reveals, but in "real life" your application could do something useful with this information.

Now you can run the Faber/Alice/Acme script from the "Preview of the Acme Controller" section above, and you should see Acme receive a proof from Alice!


## Issuing Alice a Work Credential

Now we can issue a work credential to Alice!

There are two options for this.  We can (a) add code under option ```1``` to issue the credential, or (b) we can automatically issue this credential on receipt of the education proof.

We're going to do option (a), but you can try to implement option (b) as homework.  You have most of the information you need from the proof response!

First though we need to register a schema and credential definition.  Find this code:

``` python
        # acme_schema_name = "employee id schema"
        # acme_schema_attrs = ["employee_id", "name", "date", "position"]
        await acme_agent.initialize(
            the_agent=agent,
            # schema_name=acme_schema_name,
            # schema_attrs=acme_schema_attrs,
        )

        # TODO publish schema and cred def
```

... and uncomment the code lines. Replace the ```# TODO``` comment with the following code:

``` python
        with log_timer("Publish schema and cred def duration:"):
            # define schema
            version = format(
                "%d.%d.%d"
                % (
                    random.randint(1, 101),
                    random.randint(1, 101),
                    random.randint(1, 101),
                )
            )
            # register schema and cred def
            (schema_id, cred_def_id) = await agent.register_schema_and_creddef(
                "employee id schema",
                version,
                ["employee_id", "name", "date", "position"],
                support_revocation=False,
                revocation_registry_size=TAILS_FILE_COUNT,
            )
```

For option (1) we want to replace the ```# TODO``` comment here:

``` python
            elif option == "1":
                log_status("#13 Issue credential offer to X")
                # TODO credential offers
```

with the following code:

``` python
                agent.cred_attrs[cred_def_id] = {
                    "employee_id": "ACME0009",
                    "name": "Alice Smith",
                    "date": date.isoformat(date.today()),
                    "position": "CEO"
                }
                cred_preview = {
                    "@type": CRED_PREVIEW_TYPE,
                    "attributes": [
                        {"name": n, "value": v}
                        for (n, v) in agent.cred_attrs[cred_def_id].items()
                    ],
                }
                offer_request = {
                    "connection_id": agent.connection_id,
                    "comment": f"Offer on cred def id {cred_def_id}",
                    "credential_preview": cred_preview,
                    "filter": {"indy": {"cred_def_id": cred_def_id}},
                }
                await agent.admin_POST(
                    "/issue-credential-2.0/send-offer", offer_request
                )
```

... and then locate the code that handles the credential request callback:

``` python
        if state == "request-received":
            # TODO issue credentials based on offer preview in cred ex record
            pass
```

... and replace the ```# TODO``` comment and ```pass``` statement with the following code to issue the credential as Acme offered it:

``` python
            # issue credentials based on offer preview in cred ex record
            if not message.get("auto_issue"):
                await self.admin_POST(
                    f"/issue-credential-2.0/records/{cred_ex_id}/issue",
                    {"comment": f"Issuing credential, exchange {cred_ex_id}"},
                )
```

Now you can run the Faber/Alice/Acme steps again.  You should be able to receive a proof and then issue a credential to Alice.
