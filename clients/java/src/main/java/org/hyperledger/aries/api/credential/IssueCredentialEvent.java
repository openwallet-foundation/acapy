package org.hyperledger.aries.api.credential;

import com.google.gson.annotations.SerializedName;

import lombok.Data;

/**
 * Credential that is received from a connection, usually via a webhook event.
 */
@Data
public class IssueCredentialEvent {
    private String connectionId;
    private Credential credential;
    @SerializedName(value = "cred_def_id", alternate = "credential_definition_id")
    private String credentialDefinitionId;
    private String state;
    private String role;
}
