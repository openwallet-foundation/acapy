/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.connection;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Optional;

import org.hyperledger.aries.IntegrationTestBase;
import org.hyperledger.aries.api.exception.AriesException;
import org.junit.jupiter.api.Test;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class ConnectionRecordTest extends IntegrationTestBase {

    @Test
    void testDeleteConnection() throws Exception {
        assertThrows(AriesException.class, () -> {
            ac.connectionsRemove("1");
        });
    }

    @Test
    void testCreateInvitation() throws Exception {
        final Optional<CreateInvitationResponse> inv = ac.connectionsCreateInvitation();
        assertTrue(inv.isPresent());
        assertNotNull(inv.get().getInvitationUrl());
        log.debug("{}", inv.get());
    }
}
