package org.hyperledger.aries.api.wallet;

import lombok.Data;

@Data
public class GetDidEndpointResponse {
    private String did;
    private String endpoint;
}
