/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.credential;

import static org.junit.Assert.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import java.util.Optional;

import org.hyperledger.aries.MockedTestBase;
import org.hyperledger.aries.api.credential.CredentialDefinition.CredentialDefinitionRequest;
import org.hyperledger.aries.api.credential.CredentialDefinition.CredentialDefinitionResponse;
import org.junit.jupiter.api.Test;

import okhttp3.mockwebserver.MockResponse;

class MockedCredentialTest extends MockedTestBase {

    private final String schemaId = "CHysca6fY8n8ytCDLAJGZj:2:certificate:1.0";
    private final String credentialDefinitionId = "RupFs4ns7UmyGvWKizU56o:3:CL:133:ISO9001";

    @Test
    void testCreateCredentialDefinition() throws Exception {
        server.enqueue(new MockResponse().setBody("{\n" +
                "  \"credential_definition_id\": \"JgLZdcogY4AksRvMomzDY8:3:CL:108:Agent-Test\"\n" +
                "}"));

        final Optional<CredentialDefinitionResponse> c = ac.credentialDefinitionsCreate(
                new CredentialDefinitionRequest());
        assertTrue(c.isPresent());
        assertTrue(c.get().getCredentialDefinitionId().startsWith("JgLZdcogY4AksRvMomzDY8"));
    }

    @Test
    void testGetCredentialDefinition() throws Exception {
        String json = loader.load("files/credentialDefinition.json");
        server.enqueue(new MockResponse().setBody(json));

        final Optional<CredentialDefinition> cd = ac.credentialDefinitionsGetById("mocked");
        assertTrue(cd.isPresent());
        assertEquals("108", cd.get().getSchemaId());
    }

    @Test
    void testGetCredential() throws Exception {
        String json = loader.load("files/credential.json");
        server.enqueue(new MockResponse().setBody(json));

        final Optional<Credential> credential = ac.credential("mock");
        assertTrue(credential.isPresent());
        assertTrue(credential.get().getReferent().startsWith("db439a72"));
    }

    @Test
    void testGetAllCredentials() throws Exception {
        String json = loader.load("files/credentials.json");
        server.enqueue(new MockResponse().setBody(json));

        final Optional<List<Credential>> credentials = ac.credentials();
        assertTrue(credentials.isPresent());
        assertEquals(5, credentials.get().size());
    }

    @Test
    void testGetCredentialsBySchemaId() throws Exception {
        String json = loader.load("files/credentials.json");
        server.enqueue(new MockResponse().setBody(json));

        Optional<List<Credential>> credentials = ac.credentials(
                CredentialFilter.schemaId(schemaId));
        assertTrue(credentials.isPresent());
        assertEquals(4, credentials.get().size());

        server.enqueue(new MockResponse().setBody(json));
        credentials = ac.credentials(
                CredentialFilter.schemaId(schemaId).negate());
        assertTrue(credentials.isPresent());
        assertEquals(1, credentials.get().size());
    }

    @Test
    void testGetCredentialsByCredentialDefinitionId() throws Exception {
        String json = loader.load("files/credentials.json");
        server.enqueue(new MockResponse().setBody(json));

        final Optional<List<Credential>> credentials = ac.credentials(
                CredentialFilter.credentialDefinitionId(credentialDefinitionId));
        assertTrue(credentials.isPresent());
        assertEquals(1, credentials.get().size());
    }

    @Test
    void testGetCredentialsByCredentialDefinitionIdAndSchemaId() throws Exception {
        String json = loader.load("files/credentials.json");
        server.enqueue(new MockResponse().setBody(json));

        final List<String> credentials = ac.credentialIds(
                CredentialFilter.credentialDefinitionId(credentialDefinitionId)
                .and(CredentialFilter.schemaId(schemaId)));
        assertTrue(credentials.size() == 1);
        assertEquals("60591077-717b-429b-bda1-f5930d2870c7", credentials.get(0));
    }

}
