/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.jsonld;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.hyperledger.aries.config.GsonConfig;
import org.hyperledger.aries.util.FileLoader;
import org.junit.jupiter.api.Test;

class JsonldSerialisationTest {

    private FileLoader loader = FileLoader.newLoader();

    @Test
    void testGsonSerialisation() {
        final String json = loader.load("json-ld/verifiableCredentialUnsigned.json");
        final VerifiableCredential vc = GsonConfig.defaultConfig().fromJson(json, VerifiableCredential.class);
        String vcString = GsonConfig.prettyPrinter().toJson(vc);
        assertEquals(json, vcString);
    }

}
