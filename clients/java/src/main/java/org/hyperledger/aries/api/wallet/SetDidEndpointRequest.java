package org.hyperledger.aries.api.wallet;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data @NoArgsConstructor @AllArgsConstructor @Builder
public class SetDidEndpointRequest {
    private String endpointType;
    private String did;
    private String endpoint;
}
