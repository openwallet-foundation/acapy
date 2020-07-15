package org.hyperledger.aries.api.proof;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import javax.annotation.Nullable;

import org.hyperledger.aries.api.proof.PresentProofRequest.ProofRequest.ProofAttributes.ProofRestrictions;

import com.google.gson.annotations.SerializedName;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.NonNull;

@Data @NoArgsConstructor @AllArgsConstructor
public class PresentProofRequest {

    private String connectionId;

    private ProofRequest proofRequest;

    public static PresentProofRequest build(PresentProofConfig config) {
        return new PresentProofRequest(
                config.getConnectionId(),
                ProofRequest.build(config));
    }

    @Data @NoArgsConstructor @AllArgsConstructor @Builder
    public static class ProofRequest {

        @Builder.Default
        private String name = "Proof request";

        @Builder.Default
        private String version = "1.0";

        private String nonce;

        @Builder.Default
        private Map<String, ProofAttributes> requestedAttributes = new LinkedHashMap<>();

        @Builder.Default
        private Map<String, ProofAttributes> requestedPredicates = new LinkedHashMap<>();

        public ProofRequest addRequestedAttribute(
                @NonNull String attribute, @Nullable List<ProofRestrictions> restrictions) {
            this.requestedAttributes.put(
                    attribute,
                    ProofAttributes.build(attribute, restrictions));
            return this;
        }

        @Data @NoArgsConstructor @AllArgsConstructor
        public static class ProofAttributes {
            private String name;
            private ProofNonRevoked nonRevoked;
            private List<ProofRestrictions> restrictions = new ArrayList<>();

            public static ProofAttributes build(@NonNull String name, @Nullable List<ProofRestrictions> restrictions) {
                return new ProofAttributes(name, null, restrictions);
            }

            @Data @NoArgsConstructor @AllArgsConstructor @Builder
            public static class ProofNonRevoked {
                private Integer toEpoch;
                private Integer fromEpoch;
            }

            @Data @NoArgsConstructor @AllArgsConstructor @Builder
            public static class ProofRestrictions {
                private String schemaId;

                private String schemaName;

                private String schemaVersion;

                private String schemaIssuerDid;

                @SerializedName(value = "credential_definition_id", alternate = "cred_def_id")
                private String credentialDefinitionId;

                private String issuerDid;
            }
        }

        public static ProofRequest build(@NonNull PresentProofConfig config) {
            ProofRequest result = new ProofRequest();
            config.getAttributes().forEach((k, v) -> result.addRequestedAttribute(k, v));
            return result;
        }
    }
}
