/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries;

import java.io.IOException;
import java.lang.reflect.Type;
import java.util.Collection;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

import org.hyperledger.aries.api.connection.ConnectionRecord;
import org.hyperledger.aries.api.credential.Credential;
import org.hyperledger.aries.api.exception.AriesException;
import org.hyperledger.aries.api.jsonld.ErrorResponse;
import org.hyperledger.aries.api.proof.PresentationExchangeRecord;
import org.hyperledger.aries.api.wallet.WalletDidResponse;
import org.hyperledger.aries.config.GsonConfig;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.google.gson.reflect.TypeToken;

import lombok.extern.slf4j.Slf4j;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

@Slf4j
abstract class BaseClient {

    static final MediaType JSON_TYPE = MediaType.get("application/json; charset=utf-8");

    static final Type PROOF_TYPE = new TypeToken<Collection<PresentationExchangeRecord>>(){}.getType();
    static final Type CREDENTIAL_TYPE = new TypeToken<Collection<Credential>>(){}.getType();
    static final Type CONNECTION_TYPE = new TypeToken<Collection<ConnectionRecord>>(){}.getType();
    static final Type WALLET_DID_TYPE = new TypeToken<Collection<WalletDidResponse>>(){}.getType();

    static final String X_API_KEY = "X-API-Key";

    static final String EMPTY_JSON = "{}";

    final Gson gson = GsonConfig.defaultConfig();

    final OkHttpClient client = new OkHttpClient.Builder()
            .writeTimeout(60, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .connectTimeout(60, TimeUnit.SECONDS)
            .callTimeout(60, TimeUnit.SECONDS)
            .build();

    static RequestBody jsonBody(String json) {
        return RequestBody.create(json, JSON_TYPE);
    }

    <T> Optional<T> call(Request req, Class<T> t) throws IOException {
        return call(req, (Type) t);
    }

    <T> Optional<T> call(Request req, Type t) throws IOException {
        Optional<T> result = Optional.empty();
        try (Response resp = client.newCall(req).execute()) {
            if (resp.isSuccessful() && resp.body() != null) {
                result = Optional.of(gson.fromJson(resp.body().string(), t));
            } else if (!resp.isSuccessful()) {
                log.error("code={} message={}", Integer.valueOf(resp.code()), resp.message());
                throw new AriesException(resp.code(), resp.message());
            }
        }
        return result;
    }

    Optional<String> raw(Request req) throws IOException {
        Optional<String> result = Optional.empty();
        try (Response resp = client.newCall(req).execute()) {
            if (resp.isSuccessful() && resp.body() != null) {
                result = Optional.of(resp.body().string());
            } else if (!resp.isSuccessful()) {
                log.error("code={} message={}", Integer.valueOf(resp.code()), resp.message());
                throw new AriesException(resp.code(), resp.message());
            }
        }
        return result;
    }

    void call(Request req) throws IOException {
        try (Response resp = client.newCall(req).execute()) {
            if (!resp.isSuccessful()) {
                log.error("code={} message={}", Integer.valueOf(resp.code()), resp.message());
                throw new AriesException(resp.code(), resp.message());
            }
        }
    }

    public <T> Optional<T> getWrapped(Optional<String> json, String field, Type t) {
        if (json.isPresent()) {
            JsonElement je = JsonParser
                    .parseString(json.get())
                    .getAsJsonObject()
                    .get(field);
            return Optional.ofNullable(gson.fromJson(je, t));
        }
        return Optional.empty();
    }

    public void checkForError(Optional<String> json) {
        if (json.isPresent()) {
            ErrorResponse error = gson.fromJson(json.get(), ErrorResponse.class);
            if (error != null && error.getError() != null) {
                throw new AriesException(0, error.getError());
            }
        }
    }
}
