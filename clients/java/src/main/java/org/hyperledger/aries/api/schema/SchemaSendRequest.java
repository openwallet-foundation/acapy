/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.schema;

import java.util.List;

import javax.annotation.Nonnull;

import lombok.Builder;
import lombok.Data;

@Data @Builder
public class SchemaSendRequest {
    @Nonnull
    private List<String> attributes;
    @Nonnull
    private String schemaName;
    @Nonnull
    private String schemaVersion;
}
