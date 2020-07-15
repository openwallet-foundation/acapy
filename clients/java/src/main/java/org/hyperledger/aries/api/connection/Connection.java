package org.hyperledger.aries.api.connection;

import org.apache.commons.lang3.StringUtils;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.experimental.Accessors;

@Data @NoArgsConstructor @Accessors(chain = true)
public class Connection {

    private String theirLabel;

    private String theirDid;

    private String myDid;

    private String connectionId;

    private String state;

    private String createdAt;

    private String updatedAt;

    private String alias;

    private String initiator;

    private String invitationKey;

    private String invitationMode;

    private String routingState;

    private String accept;

    public boolean isIncomingConnection() {
        return StringUtils.isNotEmpty(invitationKey);
    }

    public boolean isActive() {
        return StringUtils.isNotEmpty(state) && state.equals("active");
    }
}
