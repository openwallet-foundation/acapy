/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.config;

import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;

import lombok.NonNull;

public class TimeUtil {

    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ISO_INSTANT;

    public static String currentTimeFormatted() {
        return currentTimeFormatted(Instant.now());
    }

    public static String currentTimeFormatted(@NonNull Instant instant) {
        return FORMATTER.format(instant.truncatedTo(ChronoUnit.SECONDS));
    }
}
