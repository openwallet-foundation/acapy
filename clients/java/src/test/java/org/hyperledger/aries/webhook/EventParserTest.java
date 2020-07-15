package org.hyperledger.aries.webhook;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.Optional;

import org.hyperledger.aries.api.connection.Connection;
import org.hyperledger.aries.api.credential.IssueCredentialEvent;
import org.hyperledger.aries.api.proof.PresentProofPresentation;
import org.hyperledger.aries.pojo.AttributeName;
import org.hyperledger.aries.util.FileLoader;
import org.junit.jupiter.api.Test;

import lombok.Data;
import lombok.NoArgsConstructor;

public class EventParserTest {

    private FileLoader loader = FileLoader.newLoader();
    private EventParser parser = new EventParser();

    @Test
    void testParseConnectionEvent() {
        String json = loader.load("events/connection-active.json");
        Optional<Connection> conn = parser.parseValueSave(json, Connection.class);
        assertTrue(conn.isPresent());
        assertEquals("active", conn.get().getState());
    }

    @Test
    void testParseIssuedCredential() {
        String json = loader.load("events/issue-credential.json");
        Optional<IssueCredentialEvent> con = parser.parseValueSave(json, IssueCredentialEvent.class);
        assertTrue(con.isPresent());
        IssueCredentialEvent cred = con.get();
        assertEquals("holder", cred.getRole());
        assertNotNull(cred.getCredentialDefinitionId());
        assertNotNull(cred.getCredential());
    }

    @Test
    void testParseProofPresentation() throws Exception {
        String json = loader.load("events/proof-valid.json");
        Optional<PresentProofPresentation> p = parser.parsePresentProof(json);
        assertTrue(p.isPresent());
        assertEquals("verifier", p.get().getRole());
        Masterdata md = p.get().from(Masterdata.class);
        assertEquals("4", md.getStreetNumber());
        assertEquals("8000", md.getPostalCode());
        assertNotNull(p.get().getIdentifiers());
        assertEquals(1, p.get().getIdentifiers().size());
        assertTrue(p.get().getIdentifiers().get(0).getSchemaId().startsWith("CHysca6fY8n8ytCDLAJGZj"));
        assertTrue(p.get().getIdentifiers().get(0).getCredentialDefinitionId().startsWith("CHysca6fY8n8ytCDLAJGZj"));
    }

    @Data @NoArgsConstructor
    public static final class Masterdata {
        private String name;
        @AttributeName("local_name")
        private String localName;
        private String street;
        @AttributeName("street_number")
        private String streetNumber;
        private String city;
        private String state;
        @AttributeName("postal_code")
        private String postalCode;
        private String country;
        private String website;
        private String phone;
        private String email;
        @AttributeName("registration_number")
        private String registrationNumber;
        @AttributeName("registration_country")
        private String registrationCountry;
    }
}
