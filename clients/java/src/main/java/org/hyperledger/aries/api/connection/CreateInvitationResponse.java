package org.hyperledger.aries.api.connection;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data @NoArgsConstructor @AllArgsConstructor
public class CreateInvitationResponse {
    private String invitationUrl;
    private String connectionId;
}
