/** 
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 * 
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.credential;

import java.util.Map;

import com.google.gson.annotations.SerializedName;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data @NoArgsConstructor @AllArgsConstructor
public class Credential {

    private String referent;

    private Map<String, String> attrs;

    private String schemaId;

    @SerializedName(value = "credential_definition_id", alternate = "cred_def_id")
    private String credentialDefinitionId;

    private String revRegId;

    private String credRevId;
}
