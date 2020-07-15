package org.hyperledger.aries.api.connection;

import javax.annotation.Nullable;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.NonNull;

@Data @NoArgsConstructor @AllArgsConstructor
public class Invitation {
    @NonNull private String did;
    @Nullable private String label;
}
