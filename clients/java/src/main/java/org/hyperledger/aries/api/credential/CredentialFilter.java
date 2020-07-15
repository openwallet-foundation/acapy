package org.hyperledger.aries.api.credential;

import java.util.function.Predicate;

import lombok.NonNull;

public class CredentialFilter {

    public static Predicate<Credential> credentialDefinitionId(
            @NonNull String credentialDefinitionId) {
        return c -> credentialDefinitionId.equals(c.getCredentialDefinitionId());
    }

    public static Predicate<Credential> schemaId(
            @NonNull String schemaId) {
        return c -> schemaId.equals(c.getSchemaId());
    }
}
