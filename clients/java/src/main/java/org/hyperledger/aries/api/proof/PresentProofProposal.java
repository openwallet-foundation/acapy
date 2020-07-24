/**
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.api.proof;

import java.util.List;

import org.hyperledger.aries.api.credential.CredentialAttributes;

import com.google.gson.annotations.SerializedName;

import lombok.Data;
import lombok.NoArgsConstructor;

@Data @NoArgsConstructor
public class PresentProofProposal {

    private String connectionId;

    private PresentationProposal presentationProposal;

    public PresentProofProposal(String connectionId, List<CredentialAttributes> attr) {
        super();
        this.connectionId = connectionId;
        this.presentationProposal = new PresentationProposal(attr);
    }

    @Data @NoArgsConstructor
    public static final class PresentationProposal {
        @SerializedName("@type")
        private String type = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/1.0/presentation-preview";
        private List<CredentialAttributes> attributes = List.of();
        private List<Predicate> predicates = List.of();
        public PresentationProposal(List<CredentialAttributes> attributes) {
            super();
            this.attributes = attributes;
        }
    }

    @Data @NoArgsConstructor
    public static final class Predicate {
        private String name;
        @SerializedName(value = "cred_def_id", alternate = "credential_definition_id")
        private String credentialDefinitionId;
        private String predicate;
        private Integer treshold;
    }

}
