package org.hyperledger.aries.api.proof;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import javax.annotation.Nonnull;
import javax.annotation.Nullable;

import org.hyperledger.aries.api.proof.PresentProofRequest.ProofRequest.ProofAttributes.ProofRestrictions;
import org.hyperledger.aries.pojo.PojoProcessor;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.NonNull;
import lombok.experimental.Accessors;

@Data @NoArgsConstructor @AllArgsConstructor @Accessors(chain = true)
public class PresentProofConfig {

    private String connectionId;

    private Map<String, List<ProofRestrictions>> attributes = new LinkedHashMap<>();

    @NoArgsConstructor
    public static final class PresentProofConfigBuilder {

        private String cId;

        private Map<String, List<ProofRestrictions>> attributes = new LinkedHashMap<>();

        public PresentProofConfigBuilder connectionId(String connectionId) {
            this.cId = connectionId;
            return this;
        }

        /**
         * Build requested attribute names and restrictions from class template.
         * @param <T> The class type
         * @param type Takes the attribute names from the types public field names
         * @param restriction same restriction is applied to all attribute names
         * @return {@link PresentProofConfigBuilder}
         */
        public @Nonnull <T> PresentProofConfigBuilder appendAttribute(
                @NonNull Class<T> type, @Nullable ProofRestrictions restriction) {

            PojoProcessor.fieldNames(type).forEach(name -> {
                attributes.put(name, List.of(restriction));
            });
            return this;
        }

        /**
         * Build requested attribute names and restrictions from a list of Strings
         * @param names List of requested attribute names
         * @param resriction same restriction is applied to all attribute names
         * @return {@link PresentProofConfigBuilder}
         */
        public PresentProofConfigBuilder appendAttribute(
                @NonNull List<String> names, @Nullable ProofRestrictions resriction) {

            names.forEach(name -> {
                attributes.put(name, List.of(resriction));
            });
            return this;
        }

        /**
         * More fine grained, allows to set multiple restrictions per requested attribute
         * @param name the requested attribute name
         * @param restrictions List of restrictions applied to the requested attribute
         * @return {@link PresentProofConfigBuilder}
         */
        public PresentProofConfigBuilder appendAttribute(
                @NonNull String name, @Nullable List<ProofRestrictions> restrictions) {
            attributes.put(name, restrictions);
            return this;
        }

        public PresentProofConfig build() {
            return new PresentProofConfig(cId, attributes);
        }
    }

    public static PresentProofConfigBuilder builder() {
        return new PresentProofConfigBuilder();
    }
}
