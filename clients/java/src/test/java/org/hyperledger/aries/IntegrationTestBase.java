/** 
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 * 
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries;

import org.junit.jupiter.api.BeforeEach;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.output.Slf4jLogConsumer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@Testcontainers
public abstract class IntegrationTestBase {

    private static final String ARIES_VERSION = "bcgovimages/aries-cloudagent:py36-1.15-0_0.5.2";
    private static final Integer ARIES_ADMIN_PORT = Integer.valueOf(8031);

    protected AriesClient ac;

    @Container
    protected GenericContainer<?> ariesContainer = new GenericContainer<>(ARIES_VERSION)
            .withExposedPorts(ARIES_ADMIN_PORT)
            .withCommand("start"
                    + " -it http 0.0.0.0 8030"
                    + " -ot http --admin 0.0.0.0 " + ARIES_ADMIN_PORT
                    + " --admin-insecure-mode"
                    + " --log-level info"
                    + " --plugin aries_cloudagent.messaging.jsonld")
            .waitingFor(Wait.defaultWaitStrategy())
            .withLogConsumer(new Slf4jLogConsumer(log))
            ;

    @BeforeEach
    void setup() {
        ac = new AriesClient("http://localhost:" + ariesContainer.getMappedPort(ARIES_ADMIN_PORT.intValue()), null);
    }
}
