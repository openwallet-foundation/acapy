/** 
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 * 
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.wallet;

import lombok.Data;

@Data
public class GetDidEndpointResponse {
    private String did;
    private String endpoint;
}
