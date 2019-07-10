
# Acme Controller Workshop

In this workshop we will add some functionality to a third participant in the Alice/Faber drama - namely, Acme Inc.  After completing her education at Faber College, Alice is going to apply for a job at Acme Inc.  To do this she must provide proof of education (once she has completed the interview and other non-Indy tasks), and then Acme will issue her an employment credential.


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

TODO


## Issuing Alice a Work Credential

TODO
