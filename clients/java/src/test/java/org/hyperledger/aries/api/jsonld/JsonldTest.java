/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.jsonld;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.Optional;

import org.hyperledger.aries.IntegrationTestBase;
import org.hyperledger.aries.api.jsonld.SignRequest.SignDocument;
import org.hyperledger.aries.api.jsonld.SignRequest.SignDocument.Options;
import org.hyperledger.aries.api.wallet.WalletDidResponse;
import org.hyperledger.aries.config.GsonConfig;
import org.hyperledger.aries.util.FileLoader;
import org.junit.jupiter.api.Test;

import com.google.gson.Gson;
import com.google.gson.JsonElement;

import lombok.extern.slf4j.Slf4j;

@Slf4j
class JsonldTest extends IntegrationTestBase {

    private Gson gson = GsonConfig.defaultConfig();
    private Gson pretty = GsonConfig.prettyPrinter();
    private FileLoader loader = FileLoader.newLoader();

    @Test
    void testSignAndVerifyVC() throws Exception {

        // first ceate a local did
        WalletDidResponse localDid = createLocalDid();

        VerifiableCredential vc = VerifiableCredential.builder().build();

        SignRequest sr = SignRequest.from(
                localDid.getVerkey(),
                vc,
                Options.builderWithDefaults().verificationMethod("something").build());

        log.debug("sign request: \n{}", pretty.toJson(sr));

        // sign the structure
        Optional<VerifiableCredential> signed = ac.jsonldSign(sr, VerifiableCredential.class);
        assertTrue(signed.isPresent());
        assertNotNull(signed.get().getProof());
        assertEquals("Ed25519Signature2018", signed.get().getProof().getType());
        assertTrue(signed.get().getProof().getJws().startsWith("eyJhbGciOiA"));

        // verify the structure
        final Optional<VerifyResponse> verified = ac.jsonldVerify(localDid.getVerkey(), signed.get());
        assertTrue(verified.isPresent());
        assertTrue(verified.get().isValid());
    }

    @Test
    void testSignAndVerifyVP() throws Exception {

        // first ceate a local did
        WalletDidResponse localDid = createLocalDid();

        String json = loader.load("json-ld/verifiablePresentationUnsigned.json");
        VerifiablePresentation vp = gson.fromJson(json, VerifiablePresentation.class);

        JsonElement jsonTree = gson.toJsonTree(vp);

        SignRequest sr = SignRequest.builder()
                .verkey(localDid.getVerkey())
                .doc(SignDocument.builder()
                        .credential(jsonTree.getAsJsonObject())
                        .options(Options.builder()
                                .verificationMethod("something")
                                .build())
                        .build())
                .build();

        log.debug("sign request: \n{}", pretty.toJson(sr));

        // sign the structure
        Optional<VerifiablePresentation> signed = ac.jsonldSign(sr, VerifiablePresentation.class);
        assertTrue(signed.isPresent());
        assertNotNull(signed.get().getProof());
        assertEquals("Ed25519Signature2018", signed.get().getProof().getType());
        assertTrue(signed.get().getProof().getJws().startsWith("eyJhbGciOiA"));

        // verify the structure
        final Optional<VerifyResponse> verified = ac.jsonldVerify(localDid.getVerkey(), signed.get());
        assertTrue(verified.isPresent());
        assertTrue(verified.get().isValid());
    }

    @Test
    void testVerifyWrongCredentialType() {
        assertThrows(IllegalStateException.class, () -> {
            ac.jsonldVerify("1234", new Object());
        });
    }

    private WalletDidResponse createLocalDid() throws Exception {
        final Optional<WalletDidResponse> localDid = ac.walletDidCreate();
        assertTrue(localDid.isPresent());
        log.debug("localDid: {}", localDid.get());
        return localDid.get();
    }

}
