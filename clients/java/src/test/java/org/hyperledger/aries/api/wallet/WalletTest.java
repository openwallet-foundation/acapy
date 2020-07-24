/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.wallet;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import java.util.Optional;

import org.hyperledger.aries.IntegrationTestBase;
import org.junit.jupiter.api.Test;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class WalletTest extends IntegrationTestBase {

    @Test
    void testCreateAndListWalletDids() throws Exception {

        // as the wallet is empty by default create local did first
        final Optional<WalletDidResponse> localDid = ac.walletDidCreate();
        assertTrue(localDid.isPresent());
        assertNotNull(localDid.get().getVerkey());

        // list all dids
        final Optional<List<WalletDidResponse>> walletDid = ac.walletDid();
        assertTrue(walletDid.isPresent());
        assertEquals(1, walletDid.get().size());
        walletDid.get().forEach(did -> {
            log.debug("{}", did);
        });
    }

    @Test
    void testGetPublicDid() throws Exception {
        final Optional<WalletDidResponse> publicDid = ac.walletDidPublic();
        assertTrue(publicDid.isEmpty());
    }

    @Test
    void testSetGetDidEndpoint() throws Exception {
        final Optional<WalletDidResponse> localDid = ac.walletDidCreate();
        assertTrue(localDid.isPresent());

        final String url = "http://localhost:8031";
        SetDidEndpointRequest req = SetDidEndpointRequest
                .builder()
                // .endpointType("masterdata")
                .endpoint(url)
                .did(localDid.get().getDid())
                .build();
        ac.walletSetDidEndpoint(req);

        final Optional<GetDidEndpointResponse> endp = ac.walletGetDidEndpoint(localDid.get().getDid());
        assertTrue(endp.isPresent());
        assertEquals(url, endp.get().getEndpoint());
    }
}
