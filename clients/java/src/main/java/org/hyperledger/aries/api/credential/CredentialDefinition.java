/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.credential;

import com.google.gson.JsonObject;
import com.google.gson.annotations.SerializedName;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Schemas are the same for all clients once they are agreed upon.
 */
@Data @NoArgsConstructor @AllArgsConstructor
public class CredentialDefinition {

    private String ver;

    private String id;

    @SerializedName("schemaId")
    private String schemaId;

    private String type;

    private JsonObject value;

    @Data @NoArgsConstructor @AllArgsConstructor
    public static class CredentialDefinitionRequest {
        private String tag;
        boolean supportRevocation;
        private String schemaId;
    }

    @Data @NoArgsConstructor @AllArgsConstructor
    public static class CredentialDefinitionResponse {
        @SerializedName(value = "cred_def_id", alternate = "credential_definition_id")
        private String credentialDefinitionId;
    }
}
