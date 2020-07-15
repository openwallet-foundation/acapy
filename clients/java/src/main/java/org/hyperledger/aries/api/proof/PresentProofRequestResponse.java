package org.hyperledger.aries.api.proof;

import org.hyperledger.aries.api.proof.PresentProofRequest.ProofRequest;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data @AllArgsConstructor @NoArgsConstructor
public class PresentProofRequestResponse {
    private String presentationExchangeId;
    private String threadId;
    private ProofRequest presentationRequest;
}
