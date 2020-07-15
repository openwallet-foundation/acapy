package org.hyperledger.aries.api.proof;

import static org.junit.Assert.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import java.util.Optional;

import org.hyperledger.aries.MockedTestBase;
import org.hyperledger.aries.config.GsonConfig;
import org.junit.jupiter.api.Test;

import com.google.gson.Gson;

import okhttp3.mockwebserver.MockResponse;

public class MockedPresentProofTest extends MockedTestBase {

    private Gson gson = GsonConfig.defaultConfig();

    @Test
    void testParsePresentationResponse() throws Exception {
        String json = loader.load("files/present-proof-request-response.json");
        PresentProofRequestResponse response = gson.fromJson(json, PresentProofRequestResponse.class);
        assertEquals("23243302324860431744596330413752559589", response.getPresentationRequest().getNonce());
    }

    @Test
    void TestGetPresentationExchangeRecords() throws Exception {
        String json = loader.load("files/present-proof-records.json");
        server.enqueue(new MockResponse().setBody(json));

        final Optional<List<PresentProofPresentation>> res = ac.presentProofRecords();

        assertTrue(res.isPresent());
        assertEquals(2, res.get().size());
        assertTrue(res.get().get(1).getConnectionId().startsWith("d6cf95bd"));
    }

    @Test
    void TestGetPresentationExchangeRecord() throws Exception {
        String json = loader.load("files/present-proof-record.json");
        server.enqueue(new MockResponse().setBody(json));

        final Optional<PresentProofPresentation> res = ac.presentProofRecord("mock");

        assertTrue(res.isPresent());
        assertTrue(res.get().getConnectionId().startsWith("00598f57"));
        System.err.println(res.get());
    }
}
