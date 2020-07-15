package org.hyperledger.aries.api.credential;


import java.lang.reflect.Field;
import java.security.AccessController;
import java.security.PrivilegedAction;
import java.util.ArrayList;
import java.util.List;

import javax.annotation.Nullable;

import org.apache.commons.lang3.StringUtils;
import org.hyperledger.aries.pojo.AttributeName;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.NonNull;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Data @NoArgsConstructor @AllArgsConstructor
public class CredentialAttributes {

    private String name;
    private String value;
    private String credentialDefinitionId;

    public CredentialAttributes(String name, String value) {
        this.name = name;
        this.value = value;
    }

    public static <T> List<CredentialAttributes> from(@NonNull T instance) {
        return from(instance, null);
    }

    public static <T> List<CredentialAttributes> from(
            @NonNull T instance,
            @Nullable String credentialDefinitionId) {
        List<CredentialAttributes> result = new ArrayList<>();
        Field[] fields = instance.getClass().getDeclaredFields();
        AccessController.doPrivileged((PrivilegedAction<Void>) () -> {
            for (int i = 0; i < fields.length; i++) {
                String fieldName = fields[i].getName();
                AttributeName a = fields[i].getAnnotation(AttributeName.class);
                if (a == null || !a.excluded()) {
                    String fieldValue = "";
                    try {
                        fields[i].setAccessible(true);
                        Object fv = fields[i].get(instance);
                        if (fv != null) {
                            fieldValue = fv.toString();
                        }
                    } catch (IllegalAccessException | IllegalArgumentException e) {
                        log.error("Could not get value of field: {}", fieldName, e);
                    }
                    if (StringUtils.isNotEmpty(credentialDefinitionId)) {
                        result.add(new CredentialAttributes(fieldName, fieldValue, credentialDefinitionId));
                    } else {
                        result.add(new CredentialAttributes(fieldName, fieldValue));
                    }
                }
            }
            return null; // nothing to return
        });
        return result;
    }
}
