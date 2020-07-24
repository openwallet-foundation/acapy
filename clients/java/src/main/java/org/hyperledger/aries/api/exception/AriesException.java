/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.exception;

import lombok.Getter;

public class AriesException extends RuntimeException {

    private static final long serialVersionUID = 3021451664229724966L;

    @Getter private final int code;
    @Getter private final String message;

    public AriesException (int code, String message) {
        super(message);
        this.code = code;
        this.message = message;
    }
}
