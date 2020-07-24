/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.credential;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;

import org.hyperledger.aries.pojo.AttributeName;
import org.junit.jupiter.api.Test;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

public class CredentialAttributesTest {

    @Test
    void testNoExclusions() throws Exception {
        List<CredentialAttributes> creds = CredentialAttributes.from(
                new ConcreteCredential("testname", "teststreet", "bar"));
        assertEquals(3, creds.size());
        assertEquals("name", creds.get(0).getName());
        assertEquals("testname", creds.get(0).getValue());
    }

    @Test
    void testWithExclusions() throws Exception {
        List<CredentialAttributes> creds = CredentialAttributes.from(
                new ConcreteCredentialWithExclusion());
        assertEquals(2, creds.size());
    }

    @Data @NoArgsConstructor @AllArgsConstructor
    static class ConcreteCredential {
        private String name;
        private String street;
        private String other_foo;
    }

    @Data @NoArgsConstructor @AllArgsConstructor
    static class ConcreteCredentialWithExclusion {
        private String name;
        private String street;
        @AttributeName(excluded = true)
        private String other;
    }
}
