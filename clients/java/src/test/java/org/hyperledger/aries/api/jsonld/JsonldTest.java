package org.hyperledger.aries.api.jsonld;

import static org.junit.Assert.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.Optional;

import org.hyperledger.aries.IntegrationTestBase;
import org.hyperledger.aries.api.jsonld.SignRequest.SignDocument;
import org.hyperledger.aries.api.jsonld.SignRequest.SignDocument.Credential;
import org.hyperledger.aries.api.jsonld.SignRequest.SignDocument.Options;
import org.hyperledger.aries.api.jsonld.VerifyRequest.VerifyDocument;
import org.hyperledger.aries.api.wallet.WalletDidResponse;
import org.junit.jupiter.api.Test;

import lombok.extern.slf4j.Slf4j;

@Slf4j
class JsonldTest extends IntegrationTestBase {

    @Test
    void testSignAndVerify() throws Exception {

        // first ceate a local did
        final Optional<WalletDidResponse> localDid = ac.walletDidCreate();
        assertTrue(localDid.isPresent());
        log.debug("localDid: {}", localDid.get());

        SignRequest sr = SignRequest.builder()
                .verkey(localDid.get().getVerkey())
                .doc(SignDocument.builder()
                        .credential(Credential.builder().build())
                        .options(Options.builder()
                                .verificationMethod("something")
                                .build())
                        .build())
                .build();

        // sign the structure
        Optional<SignResponse> signed = ac.jsonldSign(sr);
        assertTrue(signed.isPresent());
        assertEquals("Ed25519Signature2018", signed.get().getProof().getType());
        assertTrue(signed.get().getProof().getJws().startsWith("eyJhbGciOiA"));

        // verify the structure
        VerifyRequest vr = VerifyRequest.builder()
                .verkey(localDid.get().getVerkey())
                .doc(VerifyDocument.builder()
                        .context(signed.get().getContext())
                        .type(signed.get().getType())
                        .proof(signed.get().getProof())
                        .build())
                .build();
        final Optional<VerifyResponse> verified = ac.jsonldVerify(vr);
        assertTrue(verified.isPresent());
        assertTrue(verified.get().isValid());
    }

}
