/** 
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 * 
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.jsonld;

import lombok.Data;
import lombok.NoArgsConstructor;

@Data @NoArgsConstructor
public class VerifyResponse {
    private boolean valid;
}
