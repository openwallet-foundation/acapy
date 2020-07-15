/** 
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 * 
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.webhook;

import java.lang.reflect.Field;
import java.lang.reflect.Type;
import java.security.AccessController;
import java.security.PrivilegedAction;
import java.util.Collection;
import java.util.List;
import java.util.Map.Entry;
import java.util.Optional;
import java.util.Set;

import org.hyperledger.aries.api.proof.PresentProofPresentation;
import org.hyperledger.aries.api.proof.PresentProofPresentation.Identifier;
import org.hyperledger.aries.config.GsonConfig;
import org.hyperledger.aries.pojo.AttributeName;
import org.hyperledger.aries.pojo.PojoProcessor;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.google.gson.JsonSyntaxException;
import com.google.gson.reflect.TypeToken;

import lombok.NonNull;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class EventParser {

    private static final Type IDENTIFIER_TYPE = new TypeToken<Collection<Identifier>>(){}.getType();

    private final Gson gson = GsonConfig.defaultConfig();
    private final Gson pretty = GsonConfig.prettyPrinter();

    public String prettyJson(@NonNull String json) {
        JsonElement el = JsonParser.parseString(json);
        return pretty.toJson(el);
    }

    public <T> Optional<T> parseValueSave(@NonNull String json, @NonNull Class<T> valueType) {
        Optional<T> t = Optional.empty();
        try {
            t = Optional.ofNullable(gson.fromJson(json, valueType));
        } catch (JsonSyntaxException e) {
            log.error("Could not format json body", e);
        }
        return t;
    }

    public Optional<PresentProofPresentation> parsePresentProof(String json) {
        Optional<PresentProofPresentation> presentation = parseValueSave(json, PresentProofPresentation.class);
        if (presentation.isPresent()) {
            JsonElement je = presentation.get()
                    .getPresentation()
                    .getAsJsonObject().get("identifiers")
                    ;
            List<Identifier> identifiers = gson.fromJson(je, IDENTIFIER_TYPE);
            presentation.get().setIdentifiers(identifiers);
        }
        return presentation;
    }

    /**
     * @param <T> The class type
     * @param json present_proof.presentation
     * @param type POJO instance
     * @return Instantiated type with all matching properties set
     */
    public static <T> T from(@NonNull String json, @NonNull Class<T> type) {
        T result = PojoProcessor.getInstance(type);

        Set<Entry<String, JsonElement>> revealedAttrs = getRevealedAttributes(json);
        Field[] fields = type.getDeclaredFields();
        AccessController.doPrivileged((PrivilegedAction<Void>) () -> {
            for (int i = 0; i < fields.length; i++) {
                String fieldName;
                AttributeName a = fields[i].getAnnotation(AttributeName.class);
                if (a != null) {
                    fieldName = a.value();
                } else {
                    fieldName = fields[i].getName();
                }
                if (a == null || !a.excluded()) {
                    String fieldValue = getValueFor(fieldName, revealedAttrs);
                    try {
                        fields[i].setAccessible(true);
                        fields[i].set(result, fieldValue);
                    } catch (IllegalAccessException | IllegalArgumentException e) {
                        log.error("Could not set value of field: {} to: {}", fieldName, fieldValue, e);
                    }
                }
            }
            return null; // nothing to return
        });
        return result;
    }

    private static String getValueFor(String name, Set<Entry<String, JsonElement>> revealedAttrs) {
        String result = null;
        for (Entry<String, JsonElement> e : revealedAttrs) {
            String k = e.getKey();
            if (k.equals(name) || k.contains(name + "_uuid") && e.getValue() != null) {
                final JsonElement raw = e.getValue().getAsJsonObject().get("raw");
                if (raw != null) {
                    result = raw.getAsString();
                }
                break;
            }
        }
        return result;
    }

    private static Set<Entry<String, JsonElement>> getRevealedAttributes(String json) {
        return JsonParser
                .parseString(json)
                .getAsJsonObject().get("requested_proof")
                .getAsJsonObject().get("revealed_attrs").getAsJsonObject()
                .entrySet()
                ;
    }

}
