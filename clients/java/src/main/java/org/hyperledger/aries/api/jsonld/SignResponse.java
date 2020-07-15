package org.hyperledger.aries.api.jsonld;

import java.util.List;

import com.google.gson.JsonObject;
import com.google.gson.annotations.SerializedName;

import lombok.Data;
import lombok.NoArgsConstructor;

@Data @NoArgsConstructor
public class SignResponse {

    @SerializedName("@context")
    private List<String> context;

    private String id;

    private List<String> type;

    private String issuer;

    // annotation needed, because the default would be issuance_date
    @SerializedName("issuanceDate")
    private String issuanceDate;

    @SerializedName("credentialSubject")
    private JsonObject credentialSubject;

    private Proof proof;

    @Data @NoArgsConstructor
    public static final class Proof {
        private String type;
        private String created;
        @SerializedName("verificationMethod")
        private String verificationMethod;
        @SerializedName("proofPurpose")
        private String proofPurpose;
        private String jws;
    }
}
