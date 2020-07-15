# ACA-PY Java Client Library

Convenience library based on okhttp and gson to interact with aries cloud agent python (aca-py) instances. It is currently work in progress and not all endpoints of the agent are present in the client.

## Implemented Endpoints

| Endpoint                                   | Implemented |
|--------------------------------------------|------------------------------|
| **present-proof**                          |                              |
| /present-proof/records                     | :white_check_mark:           |
| /present-proof/records/{pres_ex_id}        | :white_check_mark:           |
| /present-proof/send-proposal               | :white_check_mark:           |
| /present-proof/create-request              | :white_check_mark:           |
| /present-proof/send-request                | :white_check_mark:           |
| /present-proof/records/{pres_ex_id}/remove | :white_check_mark:           |
| **connection**                             |                              |
| /connections                               | :white_check_mark:           |
| /conections/create-invitation              | :white_check_mark:           |
| /connections/receive-invitation            | :white_check_mark:           |
| /connections/{id}/remove                   | :white_check_mark:           |
| /connections/send-message                  | :white_check_mark:           |
| /connections/send-ping                     | :white_check_mark:           |
| **issue-credential**                       |                              |
| /issue-credential/send                     | :white_check_mark:           |
| **credentials**                            |                              |
| /credential/{id}                           | :white_check_mark:           |
| /credential/{id}/remove                    | :white_check_mark:           |
| /credentials                               | :white_check_mark:           |
| **credential-definition**                  |                              |
| /credential-definitions                    | :white_check_mark:           |
| /credential-definitions/{id}               | :white_check_mark:           |
| **wallet**                                 |                              |
| /wallet/did                                | :white_check_mark:           |
| /wallet/did/create                         | :white_check_mark:           |
| /wallet/did/public                         | :white_check_mark:           |
| /wallet/set-did-endpoint                   | :white_check_mark:           |
| /wallet/get-did-endpoint                   | :white_check_mark:           |
| **jsonld**                                 |                              |
| /jsonld/sign                               | :white_check_mark:           |
| /jsonld/verify                             | :white_check_mark:           |

# License
Project source code files are made available under the Apache License, Version 2.0 (Apache-2.0), located in the LICENSE file. Project documentation files are made available under the Creative Commons Attribution 4.0 International License (CC-BY-4.0), available at http://creativecommons.org/licenses/by/4.0/.

## A Word on Credential Definintions

The library assumes credentials and their related credential definitions are flat Pojo's like:

```Java
@Data @NoArgsConstructor
public final class MyCredentialDefinition {
    private String street;
    
    @AttributeName("e-mail")
    private String email;       // schema attribute name is e-mail
    
    @AttributeName(excluded = true)
    private String comment;     // internal field
}
```

How fields are serialised/deseriaised can be changed by using the @AttributeName annotation.

## Rest Client

```java
AriesClient ac = new AriesClient("https://example.com ", "secret");
```

### Create connection

```java
ac.receiveInvitation(new Invitation("did", "label"), "alias").ifPresent(connection -> {
        log.debug("{}", connection.getConnectionId());
    });
```

### Issue Credential

```Java
MyCredentialDefinition myCredentialDefinition = new MyCredentialDefinition("test@myexample.com")
ac.issueCredentialSend(new IssueCredentialSend(connectionId, credentialdefinitionId, myCredentialDefinition));
```

### Present Proof Request

```Java
PresentProofConfig config = PresentProofConfig.builder
    .connectionId(connectionId)
    .appendAttribute(MyCredentialDefinition.class, ProofRestrictions.builder()
        .credentialDefinitionId(credentialDefinitionId)
        .build())
    .build();
ac.presentProofSendRequest(PresentProofRequest.build(config));
```

## Webhook Handler

Assume you have a rest controller like this to handle aca-py webhook calls

```java
@Controller
public class WebhookController {

    @Inject private EventHandler handler;

    @Post("/topic/{eventType}")
    public void ariesEvent(
            @PathVariable String eventType,
            @Body String eventBody) {
        handler.handleEvent(eventType, eventBody);
    }
}
```

Your event handler implementation can then extend the abstract EventHandler class which takes care of type conversion so that you can immediately implement your business logic.

```java
@Singleton
public class MyHandler extends EventHandler {
    @Override
    public void handleProof(PresentProofPresentation proof) {
        if (proof.isVerified() && "verifier".equals(proof.getRole())) {     // received a validated proof
            MyCredentialDefinition myCredentialDefinition = proof.from(MyCredentialDefinition.class);
            //
        }
    }
}
```


