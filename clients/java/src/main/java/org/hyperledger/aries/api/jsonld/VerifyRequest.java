package org.hyperledger.aries.api.jsonld;

import java.util.List;

import javax.annotation.Nonnull;
import javax.annotation.Nullable;

import org.hyperledger.aries.api.jsonld.SignResponse.Proof;

import com.google.gson.JsonObject;
import com.google.gson.annotations.SerializedName;

import lombok.Builder;
import lombok.Data;
import lombok.NonNull;

@Data @Builder
public class VerifyRequest {

    private String verkey;

    private VerifyDocument doc;

    @Data @Builder
    public static final class VerifyDocument {

        @Builder.Default
        @NonNull @Nonnull
        @SerializedName("@context")
        private List<String> context = List.of("https://www.w3.org/2018/credentials/v1");

        @Nullable
        private String id;

        @Builder.Default
        @NonNull @Nonnull
        private List<String> type = List.of("VerifiableCredential");

        @Nullable
        private String issuer;

        @Nullable
        @SerializedName("issuanceDate")
        private String issuanceDate;

        @Nullable
        @SerializedName("credentialSubject")
        private JsonObject credentialSubject;

        private Proof proof;
    }
}
