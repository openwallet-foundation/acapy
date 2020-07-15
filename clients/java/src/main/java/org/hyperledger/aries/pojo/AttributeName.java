package org.hyperledger.aries.pojo;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Used to influence field handling in POJOs
 */
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.FIELD})
public @interface AttributeName {

    /**
     * @return the desired name of the field
     */
    String value() default "";

    /**
     * @return if the field is excluded from processing
     */
    boolean excluded() default false;
}
