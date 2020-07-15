package org.hyperledger.aries.api.jsonld;

import java.util.List;

import javax.annotation.Nonnull;
import javax.annotation.Nullable;

import com.google.gson.JsonObject;
import com.google.gson.annotations.SerializedName;

import lombok.Builder;
import lombok.Data;
import lombok.NonNull;

@Data @Builder
public class SignRequest {

    @NonNull @Nonnull
    private String verkey;

    @NonNull @Nonnull
    private SignDocument doc;

    @Data @Builder
    public static final class SignDocument {

        @NonNull @Nonnull
        private Credential credential;

        @NonNull @Nonnull
        private Options options;

        @Data @Builder
        public static final class Credential {

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
        }

        @Data @Builder
        public static final class Options {
            @Nullable
            private String type;
            @Nullable
            private String created;
            @NonNull @Nonnull
            @SerializedName("verificationMethod")
            private String verificationMethod;
            @Nullable
            private String proofPurpose;
        }
    }
}
