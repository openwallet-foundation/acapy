# Decentralized Identity Use Case Demos

The following are some demos that you can go through to see verifiable credentials in action. For each of the demos, we've included some guidance on what you should get out of the demo - and where you should **stop** exploring the demos. Later on in this guide we have some command line demos built on current generation code for developers wanting to look at what's going on under the hood.

### Alice and Faber - edX Version

The Hyperledger Indy community is littered with "Alice and Faber" demos. Alice is a former student of [Faber College](https://en.wikipedia.org/wiki/Animal_House) (motto: Knowledge is Good), and is offered from Faber a verifiable credential that she can use to prove her educational accomplishments. Alice proves the claims in the credential to get a job at ACME Corp, and then uses a credential about her job at ACME Corp. to get a loan from Thrift Bank.

The edX course version of the Alice/Faber story is good if you are new to Indy because in going through the story you get a web interface to see the interactions/technical steps in establishing connections between agents and the process for issuing and verifying credentials. **DO NOT** look into the underlying code because it is not maintained, and it is out-of-date.

We recommend using the "In Browser" steps to run the demo vs. getting things running on your local machine.

Link: [Alice and Faber - edX Version](https://github.com/hyperledger/education/blob/master/LFS171x/indy-material/nodejs/README.md)

### BC Gov's OrgBook and Greenlight

BC Gov's Verifiable Organizations Network (VON) project implemented the first production Indy app (TheOrgBook, and now just "OrgBook") that exists to bootstrap verifiable credentials ecosystems. The Greenlight use case is a demo showing how verifiable credentials can be used for reducing the red tape businesses face in trying to get a government permit (for example, to open a restaurant). The business challenge addressed by Greenlight is figuring out what other permits and licenses need to be in place before a business can get the permit it actually wants. The demo simulates a business identifying their goal permit, seeing a roadmap of the prerequisite credentials already collected and still needed, and using links to get the needed credentials. Since in these early days of decentralized identity, business don't have their own digital wallet, in applying for each credential, each permitting service is using OrgBook to get proof of the prerequisite credentials, and issuing the new credential back to the OrgBook.

If you are interested in using/contributing to VON and OrgBook, contact the folks from BC Gov using links on https://vonx.io.

Link: [Greenlight](https://greenlight.orgbook.gov.bc.ca/) - choose the "City of Surrey - Business License"
Link: [Information about Verifiable Organizations Network (VON)](https://vonx.io)
Link: [OrgBook BC - Production Instance](https://orgbook.gov.bc.ca/)

### The ConfBook Mobile Agent Demo

The ConfBook demo was presented during the [Internet Identity Workshop](https://internetidentityworkshop.com/) (IIW) 28. The demo uses instances of the Aries Cloud Agent - Python-based services interacting with a mobile agent to issue and verify credentials. Follow along with the demo to get an Aries Mobile Agent and use it to get a verifiable credential that you control your email address, and proof the claims from that credential to get a verifiable credential that you attended a
conference.

Link: [ConfBook Demo](https://vonx.io/how_to/confbook)

> Back to the [Aries Developer - Getting Started Guide](README.md).
