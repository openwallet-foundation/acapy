/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.pojo;

import java.lang.reflect.Field;
import java.security.AccessController;
import java.security.PrivilegedAction;
import java.util.ArrayList;
import java.util.List;

import javax.annotation.Nonnull;

import lombok.NonNull;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class PojoProcessor {

    public @Nonnull static <T> List<String> fieldNames(@NonNull Class<T> type) {
        List<String> result = new ArrayList<>();
        Field[] fields = type.getDeclaredFields();

        for (int i = 0; i < fields.length; i++) {
            AttributeName an = fields[i].getAnnotation(AttributeName.class);
            if (an == null || !an.excluded()) {
                result.add(fields[i].getName());
            }
        }
        return result;
    }

    public @Nonnull static <T> T getInstance(@NonNull Class<T> type) {
        return AccessController.doPrivileged((PrivilegedAction<T>) () -> {
            T result = null;
            try {
                result = type.getConstructor().newInstance();
            } catch (Exception e) {
                String msg = "Class: " + type.getName() + " is missing a public default constructor.";
                log.error(msg, e);
                throw new RuntimeException(msg);
            }
            return result;
        });
    }
}
