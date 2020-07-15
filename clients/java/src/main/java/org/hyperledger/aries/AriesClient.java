/** 
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 * 
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.function.Predicate;
import java.util.stream.Collectors;

import javax.annotation.Nullable;

import org.apache.commons.lang3.StringUtils;
import org.hyperledger.aries.api.connection.Connection;
import org.hyperledger.aries.api.connection.ConnectionFilter;
import org.hyperledger.aries.api.connection.CreateInvitationResponse;
import org.hyperledger.aries.api.connection.Invitation;
import org.hyperledger.aries.api.credential.Credential;
import org.hyperledger.aries.api.credential.CredentialDefinition;
import org.hyperledger.aries.api.credential.CredentialDefinition.CredentialDefinitionRequest;
import org.hyperledger.aries.api.credential.CredentialDefinition.CredentialDefinitionResponse;
import org.hyperledger.aries.api.credential.CredentialFilter;
import org.hyperledger.aries.api.credential.IssueCredentialSend;
import org.hyperledger.aries.api.jsonld.SignRequest;
import org.hyperledger.aries.api.jsonld.SignResponse;
import org.hyperledger.aries.api.jsonld.VerifyRequest;
import org.hyperledger.aries.api.jsonld.VerifyResponse;
import org.hyperledger.aries.api.message.BasicMessage;
import org.hyperledger.aries.api.message.TrustPing;
import org.hyperledger.aries.api.proof.PresentProofPresentation;
import org.hyperledger.aries.api.proof.PresentProofProposal;
import org.hyperledger.aries.api.proof.PresentProofRequest;
import org.hyperledger.aries.api.proof.PresentProofRequestResponse;
import org.hyperledger.aries.api.proof.PresentProofResponse;
import org.hyperledger.aries.api.wallet.GetDidEndpointResponse;
import org.hyperledger.aries.api.wallet.SetDidEndpointRequest;
import org.hyperledger.aries.api.wallet.WalletDidResponse;

import lombok.NonNull;
import okhttp3.HttpUrl;
import okhttp3.Request;

public class AriesClient extends BaseClient {

    private final String url;
    private final String apiKey;

    /**
     * @param url The base URL without a path e.g. protocol://host:[port]
     */
    public AriesClient(@NonNull String url) {
        this(url, null);
    }

    /**
     * @param url The base URL without a path e.g. protocol://host:[port]
     * @param apiKey The API key of the aries admin endpoint
     */
    public AriesClient(@NonNull String url, @Nullable String apiKey) {
        super();
        this.url = url;
        this.apiKey = apiKey != null ? apiKey : "";
    }

    // ----------------------------------------------------
    // Connection - Connection Management
    // ----------------------------------------------------

    /**
     * Query agent-to-agent connections
     * @return List of agent-to-agent connections
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<List<Connection>> connections() throws IOException {
        return connections(null);
    }

    /**
     * Query agent-to-agent connections
     * @param filter see {@link ConnectionFilter} for prepared filters
     * @return List of agent-to-agent connections
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<List<Connection>> connections(@Nullable Predicate<Connection> filter) throws IOException {
        Optional<List<Connection>> result = Optional.empty();
        Request req = buildGet(url + "/connections");
        final Optional<String> resp = raw(req);
        if (resp.isPresent()) {
            result = getWrapped(resp, "results", CONNECTION_TYPE);
            if (result.isPresent() && filter != null) {
                result = Optional.of(result.get().stream().filter(filter).collect(Collectors.toList()));
            }
        }
        return result;
    }

    /**
     * Query agent-to-agent connections
     * @return only the connection IDs
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public List<String> connectionIds() throws IOException {
        return connectionIds(null);
    }

    /**
     * Query agent-to-agent connections
     * @param filter see {@link ConnectionFilter} for prepared filters
     * @return only the connection IDs based on the filter criteria
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public List<String> connectionIds(@Nullable Predicate<Connection> filter) throws IOException {
        List<String> result = new ArrayList<>();
        final Optional<List<Connection>> c = connections(filter);
        if (c.isPresent()) {
            result = c.get().stream().map(Connection::getConnectionId).collect(Collectors.toList());
        }
        return result;
    }

    /**
     * Remove an existing connection record
     * @param connectionId the connection id
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public void connectionsRemove(@NonNull String connectionId) throws IOException {
        Request req = buildPost(url + "/connections/" + connectionId + "/remove", EMPTY_JSON);
        call(req);
      }

    /**
     * Create a new connection invitation
     * @return {@link CreateInvitationResponse}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<CreateInvitationResponse> connectionsCreateInvitation() throws IOException {
        Request req = buildPost(url + "/connections/create-invitation", EMPTY_JSON);
        return call(req, CreateInvitationResponse.class);
    }

    /**
     * Receive a new connection invitation
     * @param invite {@link Invitation}
     * @param alias optional: alias for the connection
     * @return {@link Connection}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<Connection> connectionsReceiveInvitation(@NonNull Invitation invite, @Nullable String alias)
            throws IOException{
        HttpUrl.Builder b = HttpUrl.parse(url + "/connections/receive-invitation").newBuilder();
        if (StringUtils.isNotEmpty(alias)) {
            b.addQueryParameter("alias", alias);
        }
        Request req = buildPost(b.build().toString(), invite);
        return call(req, Connection.class);
    }

    // ----------------------------------------------------
    // Basic Message - Simple Messaging
    // ----------------------------------------------------

    /**
     * Send a basic message to a connection
     * @param connectionId the connection id
     * @param msg the message
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public void connectionsSendMessage(@NonNull String connectionId, @NonNull BasicMessage msg) throws IOException {
        Request req = buildPost(url + "/connections/" + connectionId + "/send-message", msg);
        call(req);
    }

    // ----------------------------------------------------
    // Trust Ping - Trust-ping Over Connection
    // ----------------------------------------------------

    /**
     * Send a trust ping to a connection
     * @param connectionId the connection id
     * @param comment comment for the ping message
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public void connectionsSendPing(@NonNull String connectionId, @NonNull TrustPing comment) throws IOException {
        Request req = buildPost(url + "/connections/" + connectionId + "/send-ping", comment);
        call(req);
    }

    // ----------------------------------------------------
    // Credential Definition - Credential Definition Operations
    // ----------------------------------------------------

    /**
     * Sends a credential definition to the ledger
     * @param defReq {@link CredentialDefinitionRequest}
     * @return {@link CredentialDefinitionResponse}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<CredentialDefinitionResponse> credentialDefinitionsCreate(
            @NonNull CredentialDefinitionRequest defReq) throws IOException {
        Request req = buildPost(url + "/credential-definitions", defReq);
        return call(req, CredentialDefinitionResponse.class);
    }

    /**
     * Gets a credential definition from the ledger
     * @param id credential definition id
     * @return {@link CredentialDefinition}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<CredentialDefinition> credentialDefinitionsGetById(@NonNull String id) throws IOException {
        Request req = buildGet(url + "/credential-definitions/" + id);
        final Optional<String> resp = raw(req);
        return getWrapped(resp, "credential_definition", CredentialDefinition.class);
    }

    // ----------------------------------------------------
    // Issue Credential - Credential Issue
    // ----------------------------------------------------

    /**
     * Send holder a credential, automating the entire flow
     * @param issueCredential {@link IssueCredentialSend} the credential to be issued
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public void issueCredentialSend(@NonNull IssueCredentialSend issueCredential) throws IOException {
        Request req = buildPost(url + "/issue-credential/send", issueCredential);
        call(req);
    }

    // ----------------------------------------------------
    // Credentials- Holder Credential Management
    // ----------------------------------------------------

    /**
     * Fetch credentials from wallet
     * @return list of credentials {@link Credential}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<List<Credential>> credentials() throws IOException {
        return credentials(null);
    }

    /**
     * Fetch credentials from wallet
     * @param filter see {@link CredentialFilter} for prepared filters
     * @return Credentials that match the filter criteria
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<List<Credential>> credentials(@Nullable Predicate<Credential> filter) throws IOException {
        Optional<List<Credential>> result = Optional.empty();
        Request req = buildGet(url + "/credentials");
        final Optional<String> resp = raw(req);
        if (resp.isPresent()) {
            result = getWrapped(resp, "results", CREDENTIAL_TYPE);
            if (result.isPresent() && filter != null) {
                result = Optional.of(result.get().stream().filter(filter).collect(Collectors.toList()));
            }
        }
        return result;
    }

    /**
     * Fetch credentials from wallet
     * @return only the credential IDs
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public List<String> credentialIds() throws IOException {
        return credentialIds(null);
    }

    /**
     * Fetch credentials from wallet
     * @param filter see {@link CredentialFilter} for prepared filters
     * @return only the credential IDs based on the filter criteria
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public List<String> credentialIds(@Nullable Predicate<Credential> filter) throws IOException {
        List<String> result = new ArrayList<>();
        final Optional<List<Credential>> c = credentials(filter);
        if (c.isPresent()) {
            result = c.get().stream().map(Credential::getReferent).collect(Collectors.toList());
        }
        return result;
    }

    /**
     * Fetch a credential from wallet by id
     * @param referent referent
     * @return {@link Credential}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<Credential> credential(@NonNull String referent) throws IOException {
        Request req = buildGet(url + "/credential/" + referent);
        return call(req, Credential.class);
    }

    /**
     * Remove a credential from the wallet by id (referent)
     * @param referent referent
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public void credentialRemove(@NonNull String referent) throws IOException {
        Request req = buildPost(url + "/credential/" + referent + "/remove", EMPTY_JSON);
        call(req);
    }

    // ----------------------------------------------------
    // Present Proof - Proof Presentation
    // ----------------------------------------------------

    /**
     * Fetch all present-proof exchange records
     * @return list of {@link PresentProofPresentation}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<List<PresentProofPresentation>> presentProofRecords() throws IOException {
        Request req = buildGet(url + "/present-proof/records");
        final Optional<String> resp = raw(req);
        return getWrapped(resp, "results", PROOF_TYPE);
    }

    /**
     * Fetch a single presentation exchange record by ID
     * @param presentationExchangeId the presentation exchange id
     * @return {@link PresentProofPresentation}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<PresentProofPresentation> presentProofRecord(@NonNull String presentationExchangeId)
            throws IOException {
        Request req = buildGet(url + "/present-proof/records/" + presentationExchangeId);
        return call(req, PresentProofPresentation.class);
    }

    /**
     * Sends a presentation proposal
     * @param proofProposal {@link PresentProofProposal}
     * @return {@link PresentProofResponse}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<PresentProofResponse> presentProofSendProposal(@NonNull PresentProofProposal proofProposal)
            throws IOException{
        Request req = buildPost(url + "/present-proof/send-proposal", proofProposal);
        return call(req, PresentProofResponse.class);
    }

    /**
     * Creates a presentation request not bound to any proposal or existing connection
     * @param proofRequest {@link PresentProofRequest}
     * @return {@link PresentProofRequestResponse}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<PresentProofRequestResponse> presentProofCreateRequest(@NonNull PresentProofRequest proofRequest)
            throws IOException {
        Request req = buildPost(url + "/present-proof/create-request", proofRequest);
        return call(req, PresentProofRequestResponse.class);
    }

    /**
     * Sends a free presentation request not bound to any proposal
     * @param proofRequest {@link PresentProofRequest}
     * @return {@link PresentProofResponse}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<PresentProofResponse> presentProofSendRequest(@NonNull PresentProofRequest proofRequest)
            throws IOException {
        Request req = buildPost(url + "/present-proof/send-request", proofRequest);
        return call(req, PresentProofResponse.class);
    }

    /**
     * Remove an existing presentation exchange record by ID
     * @param presentationExchangeId the presentation exchange id
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public void presentProofRecordsRemove(@NonNull String presentationExchangeId) throws IOException {
        Request req = buildPost(url + "/present-proof/records/" + presentationExchangeId + "/remove",
                EMPTY_JSON);
        call(req);
    }

    // ----------------------------------------------------
    // Wallet
    // ----------------------------------------------------

    /**
     * List wallet DIDs
     * @return list of {@link WalletDidResponse}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<List<WalletDidResponse>> walletDid() throws IOException {
        Request req = buildGet(url + "/wallet/did");
        return getWrapped(raw(req), "results", WALLET_DID_TYPE);
    }

    /**
     * Create local DID
     * @return {@link WalletDidResponse}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<WalletDidResponse> walletDidCreate() throws IOException {
        Request req = buildPost(url + "/wallet/did/create", EMPTY_JSON);
        return getWrapped(raw(req), "result", WalletDidResponse.class);
    }

    /**
     * Fetch the current public DID
     * @return {@link WalletDidResponse}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<WalletDidResponse> walletDidPublic() throws IOException {
        Request req = buildGet(url + "/wallet/did/public");
        return getWrapped(raw(req), "result", WalletDidResponse.class);
    }

    /**
     * Update end point in wallet and, if public, on ledger
     * @param endpointRequest {@link SetDidEndpointRequest}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public void walletSetDidEndpoint(@NonNull SetDidEndpointRequest endpointRequest) throws IOException {
        Request req = buildPost(url + "/wallet/set-did-endpoint", endpointRequest);
        call(req);
    }

    /**
     * Query DID end point in wallet
     * @param did the did
     * @return {@link GetDidEndpointResponse}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<GetDidEndpointResponse> walletGetDidEndpoint(@NonNull String did) throws IOException {
        Request req = buildGet(url + "/wallet/get-did-endpoint" + "?did=" + did);
        return call(req, GetDidEndpointResponse.class);
    }

    // ----------------------------------------------------
    // JSON-LD
    // ----------------------------------------------------

    /**
     * Sign a JSON-LD structure and return it
     * @since aca-py 0.5.2
     * @param signRequest {@link SignRequest}
     * @return {@link SignResponse}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<SignResponse> jsonldSign(@NonNull SignRequest signRequest) throws IOException {
        Request req = buildPost(url + "/jsonld/sign", signRequest);
        return getWrapped(raw(req), "signed_doc", SignResponse.class);
    }

    /**
     * Verify a JSON-LD structure
     * @since aca-py 0.5.2
     * @param verifyRequest {@link VerifyRequest}
     * @return {@link VerifyResponse}
     * @throws IOException if the request could not be executed due to cancellation, a connectivity problem or timeout.
     */
    public Optional<VerifyResponse> jsonldVerify(@NonNull VerifyRequest verifyRequest) throws IOException {
        Request req = buildPost(url + "/jsonld/verify", verifyRequest);
        return call(req, VerifyResponse.class);
    }

    // ----------------------------------------------------
    // Internal
    // ----------------------------------------------------

    private Request buildPost(String u, Object body) {
        return new Request.Builder()
                .url(u)
                .post(jsonBody(gson.toJson(body)))
                .header(X_API_KEY, apiKey)
                .build();
    }

    private Request buildGet(String u) {
        return new Request.Builder()
                .url(u)
                .get()
                .header(X_API_KEY, apiKey)
                .build();
    }
}
