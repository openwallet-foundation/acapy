/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.jsonld;

import javax.annotation.Nonnull;
import javax.annotation.Nullable;

import org.hyperledger.aries.api.jsonld.SignRequest.SignDocument.Options;
import org.hyperledger.aries.config.GsonConfig;
import org.hyperledger.aries.config.TimeUtil;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.annotations.SerializedName;

import lombok.Builder;
import lombok.Data;
import lombok.NonNull;

/**
 * Use the SignRequest.from() method to easily construct a new sign request.
 * <pre>{@code
 * SignRequest signRequest = SignRequest.from(
 *     verkey,
 *     verifiablePresentation,
 *     Options.builderWithDefaults()
 *         .verificationMethod("did:key:" + verkey) // self signed
 *         .build());
 * }</pre>
 */
@Data @Builder
public final class SignRequest {

    @NonNull @Nonnull
    private String verkey;

    @NonNull @Nonnull
    private SignDocument doc;

    @Data @Builder
    public static final class SignDocument {

        @NonNull @Nonnull
        private JsonObject credential;  // either VC or VP

        @NonNull @Nonnull
        private Options options;

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
            @SerializedName("proofPurpose")
            private String proofPurpose;

            public static class OptionsBuilder {} // java doc plugin cannot handle lombok

            public static OptionsBuilder builderWithDefaults() {
                return Options
                        .builder()
                        .type("Ed25519Signature2018")
                        .created(TimeUtil.currentTimeFormatted())
                        .proofPurpose("assertionMethod");
            }
        }
    }

    public static SignRequest from(String verkey, Object t, Options options) {
        if (t instanceof VerifiableCredential || t instanceof VerifiablePresentation) {
            Gson gson = GsonConfig.defaultConfig();
            return SignRequest.builder()
                    .verkey(verkey)
                    .doc(SignDocument.builder()
                            .credential(gson.toJsonTree(t).getAsJsonObject())
                            .options(options)
                            .build())
                    .build();
        }
        throw new IllegalStateException("Expecting either VerifiableCredential or VerifiablePresentation");
    }
}
