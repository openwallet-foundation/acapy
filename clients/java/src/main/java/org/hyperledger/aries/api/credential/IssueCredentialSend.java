/** 
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 * 
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.credential;

import java.util.ArrayList;
import java.util.List;

import com.google.gson.annotations.SerializedName;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.experimental.Accessors;

/**
 * Credential that is issued to a connection
 */
@Data @NoArgsConstructor @Accessors(chain = true)
public class IssueCredentialSend {

    private String connectionId;

    @SerializedName(value = "credential_definition_id", alternate = "cred_def_id")
    private String credentialDefinitionId;

    private CredentialProposal credentialProposal;

    public <T> IssueCredentialSend(
            String connectionId, String credentialDefinitionId, T instance) {
        super();
        this.connectionId = connectionId;
        this.credentialDefinitionId = credentialDefinitionId;
        this.credentialProposal = new CredentialProposal(CredentialAttributes.from(instance));
    }

    @Data @NoArgsConstructor
    public static final class CredentialProposal {

        @SerializedName("@type")
        private String type = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0/credential-preview";

        private List<CredentialAttributes> attributes = new ArrayList<>();

        public CredentialProposal(List<CredentialAttributes> attributes) {
            super();
            this.attributes = attributes;
        }
    }
}
