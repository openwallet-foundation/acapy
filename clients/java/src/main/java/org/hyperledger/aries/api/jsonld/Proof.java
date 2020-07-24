/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.jsonld;

import com.google.gson.annotations.SerializedName;

import lombok.Data;
import lombok.NoArgsConstructor;

@Data @NoArgsConstructor
public final class Proof {
    private String type;
    private String created;
    @SerializedName("verificationMethod")
    private String verificationMethod;
    @SerializedName("proofPurpose")
    private String proofPurpose;
    private String jws;
}
