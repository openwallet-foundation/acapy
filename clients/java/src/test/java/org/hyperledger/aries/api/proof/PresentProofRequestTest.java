/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.proof;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import java.util.Optional;

import org.hyperledger.aries.IntegrationTestBase;
import org.hyperledger.aries.api.proof.PresentProofRequest.ProofRequest.ProofAttributes.ProofRestrictions;
import org.junit.jupiter.api.Test;

class PresentProofRequestTest extends IntegrationTestBase {

    @Test
    void testProofCreateRequest() throws Exception {
        PresentProofConfig config = PresentProofConfig.builder()
                .appendAttribute(List.of("name", "email"), ProofRestrictions.builder().build())
                .build();
        Optional<PresentProofRequestResponse> resp = ac.presentProofCreateRequest(PresentProofRequest.build(config));
        assertTrue(resp.isPresent());
        assertNotNull(resp.get().getPresentationExchangeId());
        assertEquals(2, resp.get().getPresentationRequest().getRequestedAttributes().size());
    }

}
