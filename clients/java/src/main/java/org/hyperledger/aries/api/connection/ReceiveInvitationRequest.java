/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.connection;

import java.util.List;

import javax.annotation.Nullable;

import com.google.gson.annotations.SerializedName;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.NonNull;

@Data @NoArgsConstructor @AllArgsConstructor
public class ReceiveInvitationRequest {
    @Nullable
    @SerializedName("@id")
    private String id;

    @Nullable
    @SerializedName("routingKeys")
    private List<String> routingKeys;

    @Nullable
    @SerializedName("imageUrl")
    private String imageUrl;

    @Nullable
    @SerializedName("recipientKeys")
    private List<String> recipientKeys;

    /**
     * Only mandatory field in the request
     */
    @NonNull
    private String did;

    @Nullable
    private String serviceEndpoint;

    @Nullable
    private String label;
}
