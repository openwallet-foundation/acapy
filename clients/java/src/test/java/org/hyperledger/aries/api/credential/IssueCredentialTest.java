/** 
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 * 
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.credential;

import static org.junit.jupiter.api.Assertions.assertThrows;

import org.hyperledger.aries.IntegrationTestBase;
import org.hyperledger.aries.api.exception.AriesException;
import org.junit.jupiter.api.Test;

class IssueCredentialTest extends IntegrationTestBase {

    @Test
    void testIssueCredential() throws Exception {
        IssueCredentialSend ic = new IssueCredentialSend();
        assertThrows(AriesException.class, () -> {
            ac.issueCredentialSend(ic);
        });
    }

}
