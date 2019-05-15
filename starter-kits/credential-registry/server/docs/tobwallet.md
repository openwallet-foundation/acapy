# TheOrgBook HL-Indy Wallet Requirements

In the self-sovereign identity (SSI) world, the wallet is the go to term for the digital equivalent to the physical place you keep your primary pieces of identity - your drivers licence, credit cards, etc. The data held in the wallet depends somewhat on the role of the identity in a self-sovereign ecosystem - a claims issuer, holder (aka prover) or verifier (aka inspector). Of course, any particular identity might take on multiple roles and so have any and all types of SSI data. We expect that for most "typical" use cases for wallets, the major implementations will be provided by 3rd parties in the market. For example, there are software vendors working on mobile wallets targeting consumers, whose primary role is as a holder of claims about themselves (they are the subject of the claims). As well, we understand software vendors are also working on "Enterprise Agents" - applications that have wallets for the purpose of primarily operating as either or (more commonly, we think) both claims issuers and claim verifiers.

TheOrgBook is somewhat different from both of those "typical" models. It is primarily a claims holder, but quite a different one from a consumer-type claims holder.  Notably, it will hold Enterprise-level data volumes, and the claims that it holds are about many subjects (organizational entities) - not about itself. As such the requirements of its wallet are quite different from those of a typical consumer wallet.

A claims holder wallet (consumer or TheOrgBook) would be expected to contain the following:

* DIDs (references to decentralized IDs) that make up the wallet owner's identity, and context of those DIDs - e.g. for pair-wise DIDs, the connection to which that DID applies.
* The DIDs of your connections (e.g. your banks, stores, government services and so on)
* Verifiable credentials issued to you.
* Cryptographic materials - public and private keys associated with your DIDs, and possibly other materials such as (in the HL-Indy world) your Master Secret for requesting claims (to issuers) and providing proofs (to verifiers)

Note that the private keys may or may not (by implementation) go in the wallet - they may deliberately be kept separate to prevent the theft of a wallet giving the thief access to the use and all the information in the wallet.

While we expect the TheOrgBook wallet to hold those same pieces of data to be used for the  operations as a consumer wallet, there are several requirements that are quite different:

* The volume of claims will be much higher than a typical consumer holder wallet - on the order of millions.
* The number of claims associated with specific Schema/Issuers will be much higher than a typical consumer wallet. For example, in loading the full history of the BC Registry set of "Certificate of Incorporation" and related claims (annual reports, name changes, amalgamations, etc), there will be millions claims loaded. In a typical consumer/small business scenario there would likely be 1 or at most a small number of "Certificate of Incorporation" claims.
* Claims are about different subjects, with the unique identifier of the claim's subject embedded in a field in the claim.

## Work To Be Done

### Enterprise Level Persistence

TheOrgBook currently uses the default HL-Indy wallet implementation based on an encrypted version of SQL-Lite (SQLCipher). To both handle the volume of claims that TheOrgBook will need to support and to provide more robust database administration handling, we want to update the wallet implementation to use (likely) PostgreSQL for persistence. TheOrgBook runs on the BC Government's private Red Hat OpenShift Platform as a Service implementation, and for relational databases, PostgreSQL is the preferred choice. Note that if the developers feel that a noSQL solution would be better, we would like go to MongoDB (although Redis is available out of the box with OpenShift).

### Getting Claims for Proof Requests

The current HL-Indy wallet interface has a call that given a Proof Request (an array of claim names, each from a possibly different credential associated with one or more schema and/or issuers) returns all of the credentials in the wallet that could satisfy each claim in the Proof Request. Since, as noted above, the wallet of TheOrgBook holds the same claim for (literally) millions of subjects, Proof Requests will return from the default wallet API call millions of credentials - likely causing a significant performance issue. To prevent a performance impact we have proposed that a Proof Request can include an optional filter condition that allows the call to the wallet to filter based on claim values the credentials of interest for a given Proof Request. In case of TheOrgBook, the filter condition will usually simply be the unique identifier of the Organization of interest - the subject of the claim. Our proposal for an update to the HL-Indy Proof Request format to support this functionality can be found in the HL-Indy JIRA system ([IS-486](https://jira.hyperledger.org/projects/IS/issues/IS-486)).

While we think that change could be used to resolve this issue, we are open to other proposals. In addition, we think (but again, could be wrong) that because of the data volumes in TheOrgBook, the wallet implementation will need to do this credential filtering at as low a level as possible - ideally at the database level - to prevent the manipulation of large volumes of data for each Proof Request.
