package org.hyperledger.aries.api.connection;

import java.util.function.Predicate;

import lombok.NonNull;

public class ConnectionFilter {

    public static Predicate<Connection> alias(@NonNull String alias) {
        return c -> alias.equals(c.getAlias());
    }

    public static Predicate<Connection> theirLabel(@NonNull String theirLabel) {
        return c -> theirLabel.equals(c.getTheirLabel());
    }

    public static Predicate<Connection> state(@NonNull String state) {
        return c -> state.equals(c.getState());
    }

}
