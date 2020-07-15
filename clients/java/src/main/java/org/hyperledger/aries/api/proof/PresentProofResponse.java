package org.hyperledger.aries.api.proof;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data @NoArgsConstructor @AllArgsConstructor
public class PresentProofResponse {
    private String presentationExchangeId;
}
