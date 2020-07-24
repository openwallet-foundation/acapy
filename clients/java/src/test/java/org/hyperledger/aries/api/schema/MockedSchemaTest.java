/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.schema;

import static org.junit.Assert.assertTrue;

import java.util.List;
import java.util.Optional;

import org.hyperledger.aries.MockedTestBase;
import org.junit.jupiter.api.Test;

import lombok.extern.slf4j.Slf4j;
import okhttp3.mockwebserver.MockResponse;

@Slf4j
class MockedSchemaTest extends MockedTestBase{

    @Test
    void testSendSchema() throws Exception {
        String json = loader.load("files/schemaSendResults.json");

        server.enqueue(new MockResponse().setBody(json));

        final Optional<SchemaSendResponse> res = ac.schemas(SchemaSendRequest
                .builder()
                .schemaName("prefs")
                .schemaVersion("1.0")
                .attributes(List.of("score"))
                .build());

        assertTrue(res.isPresent());
        assertTrue(res.get().getSchemaId().startsWith("M6Mbe3qx7vB4wpZF4sBRjt"));
        assertTrue(res.get().getSchema().getId().startsWith("M6Mbe3qx7vB4wpZF4sBRjt"));
        log.debug(pretty.toJson(res.get()));
    }

}
