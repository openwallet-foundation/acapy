/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.connection;

import java.util.function.Predicate;

import lombok.NonNull;

public class ConnectionFilter {

    public static Predicate<ConnectionRecord> alias(@NonNull String alias) {
        return c -> alias.equals(c.getAlias());
    }

    public static Predicate<ConnectionRecord> theirLabel(@NonNull String theirLabel) {
        return c -> theirLabel.equals(c.getTheirLabel());
    }

    public static Predicate<ConnectionRecord> state(@NonNull String state) {
        return c -> state.equals(c.getState());
    }

}
