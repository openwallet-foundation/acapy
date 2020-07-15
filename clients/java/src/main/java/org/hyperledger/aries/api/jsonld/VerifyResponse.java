package org.hyperledger.aries.api.jsonld;

import lombok.Data;
import lombok.NoArgsConstructor;

@Data @NoArgsConstructor
public class VerifyResponse {
    private boolean valid;
}
