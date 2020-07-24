/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.pojo;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;

import org.junit.jupiter.api.Test;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

class PojoProcessorTest {

    @Test
    void testGetAttributes() {
        List<String> attr = PojoProcessor.fieldNames(ConcreteExample.class);
        assertEquals(2, attr.size());
        assertEquals("one", attr.get(0));
        assertEquals("two", attr.get(1));
    }

    @Test
    void testGetAttributesExclusion() {
        List<String> attr = PojoProcessor.fieldNames(ConcreteExampleWithExclusion.class);
        assertEquals(2, attr.size());
        assertEquals("name", attr.get(0));
        assertEquals("street", attr.get(1));
    }

    @Data @NoArgsConstructor @AllArgsConstructor
    static class ConcreteExample {
        private String one;
        private String two;
    }

    @Data @NoArgsConstructor @AllArgsConstructor
    static class ConcreteExampleWithExclusion {
        private String name;
        private String street;
        @AttributeName(excluded = true)
        private String other;
    }

}
