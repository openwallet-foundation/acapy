/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.webhook;

import org.hyperledger.aries.api.connection.ConnectionRecord;
import org.hyperledger.aries.api.credential.IssueCredentialEvent;
import org.hyperledger.aries.api.message.BasicMessage;
import org.hyperledger.aries.api.message.PingEvent;
import org.hyperledger.aries.api.proof.PresentationExchangeRecord;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public abstract class EventHandler {

    private EventParser parser = new EventParser();

    public void handleEvent(String eventType, String json) {

        handleRaw(eventType, json);

        try {
            if ("connections".equals(eventType)) {
                parser.parseValueSave(json, ConnectionRecord.class).ifPresent(connection -> {
                    handleConnection(connection);
                });
            } else if ("present_proof".equals(eventType)) {
                parser.parsePresentProof(json).ifPresent(proof -> {
                    handleProof(proof);
                });
            } else if ("issue_credential".equals(eventType)) {
                parser.parseValueSave(json, IssueCredentialEvent.class).ifPresent(credential -> {
                    handleCredential(credential);
                });
            } else if ("basicmessages".equals(eventType)) {
                parser.parseValueSave(json, BasicMessage.class).ifPresent(message -> {
                    handleBasicMessage(message);
                });
            } else if ("ping".equals(eventType)) {
                parser.parseValueSave(json, PingEvent.class).ifPresent(ping -> {
                    handlePing(ping);
                });
            }
        } catch (Exception e) {
            log.error("Error in webhook event handler:", e);
        }
    }

    public void handleConnection(ConnectionRecord connection) {
        log.debug("Connection Event: {}", connection);
    }

    public void handleProof(PresentationExchangeRecord proof) {
        log.debug("Present Proof Event: {}", proof);
    }

    public void handleCredential(IssueCredentialEvent credential) {
        log.debug("Issue Credential Event: {}", credential);
    }

    public void handleBasicMessage(BasicMessage message) {
        log.debug("Basic Message: {}", message);
    }

    public void handlePing(PingEvent ping) {
        log.debug("Ping: {}", ping);
    }

    public void handleRaw(String eventType, String json) {
        if (log.isTraceEnabled()) {
            log.trace("Received event: {}, body:\n {}", eventType, parser.prettyJson(json));
        }
    }
}
