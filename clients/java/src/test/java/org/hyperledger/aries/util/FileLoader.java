/** 
 * Copyright (c) 2020 Robert Bosch GmbH. All Rights Reserved.
 * 
 * SPDX-License-Identifier: Apache-2.0
 */
package org.hyperledger.aries.util;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.Charset;
import java.util.stream.Collectors;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class FileLoader {

    public String load(String filename) {
        String result = "";
        String fn;

        if (!filename.contains(".")) {
            fn = filename + ".json";
        } else {
            fn = filename;
        }

        InputStream is = getClass().getClassLoader().getResourceAsStream(fn);
        try (BufferedReader buffer = new BufferedReader(new InputStreamReader(is, Charset.forName("UTF-8")))) {
            result =  buffer.lines().collect(Collectors.joining("\n"));
        } catch (IOException e) {
            log.error("Could not read from imput stream.", e);
        }

        return result;
    }

    public static FileLoader newLoader() {
        return new FileLoader();
    }
}