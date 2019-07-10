
# Acme Controller Workshop

In this workshop we will add some functionality to a third participant in the Alice/Faber drama - namely, Acme Inc.  After completing her education at Faber College, Alice is going to apply for a job at Acme Inc.  To do this she must provide proof of education (once she has completed the interview and other non-Indy tasks), and then Acme will issue her an employment credential.

Note that an updated Acme controller is available here: https://github.com/ianco/aries-cloudagent-python/tree/agent_workshop/demo if you just want to skip ahead ...


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
./run_demo faber
```

... and in the second shell run Alice:

```bash
./run_demo alice
```

When Faber has produced an invitation, copy it over to Alice.

Then, in the Faber shell, select option ```1``` to issue a credential to Alice.  (You can select option ```2``` if you like, to confirm via proof.)

Then, in the Faber shell, enter ```X``` to exit the controller, and then run the Acme controller:

```bash
X
./run_demo acme
```

In the Alice shell, select option ```4``` (to enter a new invitation) and then copy over Acme's invitation once it's available.

Then, in the Acme shell, you can select option ```2``` and then option ```1```, which don't do anything ... yet!!!


## Asking Alice for a Proof of Education

In the Acme code ```acme.py``` we are going to add code to issue a proof request to Alice, and then validate the received proof.

First locate the code that is triggered by option ```2```:

```
            elif option == "2":
                log_status("#20 Request proof of degree from alice")
                # TODO presentation requests
```

Add the following code under the ```# TODO``` commment:

```
                # TODO presentation requests
                # ask for any degree, don't restrict to Faber (we can check the issuer when we receive the proof)
                proof_attrs = [
                    {"name": "name", "restrictions": [{"schema_name": "degree schema"}]},
                    {"name": "date", "restrictions": [{"schema_name": "degree schema"}]}, 
                    {"name": "degree", "restrictions": [{"schema_name": "degree schema"}]}, 
                ]
                proof_predicates = []
                proof_request = {
                    "name": "Proof of Education",
                    "version": "1.0",
                    "connection_id": agent.connection_id,
                    "requested_attributes": proof_attrs,
                    "requested_predicates": proof_predicates,
                }
                # this sends the request to our agent, which forwards it to Alice (based on the connection_id)
                await agent.admin_POST(
                    "/presentation_exchange/send_request", proof_request
                )
```

Now we need to handle receipt of the proof.  Locate the code that handles received proofs (this is in a webhook callback):

```
        if state == "presentation_received":
            # TODO handle received presentations
            pass
```

Add the following code under the ```# TODO``` comment (replace ```pass```):

```
            # TODO handle received presentations
            # if presentation is a degree schema (proof of education), check the received values
            is_proof_of_education = (message['presentation_request']['name'] == 'Proof of Education')
            if is_proof_of_education:
                log_status("#28.1 Received proof of education, check claims")
                for attr, value in message['presentation_request']['requested_attributes'].items():
                    # just print out the received claim values
                    self.log(value['name'], message['presentation']['requested_proof']['revealed_attrs'][attr]['raw'])
                for identifier in message['presentation']['identifiers']:
                    # just print out the schema/cred def id's of presented claims
                    self.log(identifier['schema_id'], identifier['cred_def_id'])
            else:
                # in case there are any other kinds of proofs received
                self.log("#28.1 Received ", message['presentation_request']['name'])
```

Right now this just prints out information received in the proof, but in "real life" your application could do somethign useful with this information.

Now you can run the Faber/Alice/Acme script from the "preview" section above, and you should see Acme receive a proof from Alice!


## Issuing Alice a Work Credential

TODO


