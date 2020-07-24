/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.jsonld;

import java.util.List;

import javax.annotation.Nonnull;
import javax.annotation.Nullable;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import com.google.gson.annotations.SerializedName;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.NonNull;

/**
 * @see <a href="https://www.w3.org/2018/credentials/v1#VerifiablePresentation">VerifiablePresentation</a>
 *
 */
@Data @Builder @NoArgsConstructor @AllArgsConstructor
@JsonPropertyOrder({ "@context", "type" })
public class VerifiablePresentation {

    @Builder.Default
    @NonNull @Nonnull
    @SerializedName("@context")
    @JsonProperty("@context")
    private List<String> context = List.of("https://www.w3.org/2018/credentials/v1");

    @Nullable
    private String id;

    @Builder.Default
    @NonNull @Nonnull
    private List<String> type = List.of("VerifiablePresentation");

    @Nullable
    @SerializedName("verifiableCredential")
    private List<VerifiableCredential> verifiableCredential;

    @Nullable
    private Proof proof;
}
