package org.hyperledger.aries.api.wallet;

import com.google.gson.annotations.SerializedName;

import lombok.Data;
import lombok.NoArgsConstructor;

@Data @NoArgsConstructor
public class WalletDidResponse {
    private String did;
    private String verkey;
    @SerializedName("public")
    private boolean isPublic;
}
