/*
 * micro
 * Copyright (C) 2017 micro contributors
 *
 * This program is free software: you can redistribute it and/or modify it under the terms of the
 * GNU Lesser General Public License as published by the Free Software Foundation, either version 3
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
 * even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License along with this program.
 * If not, see <http://www.gnu.org/licenses/>.
 */

/* eslint-env node */

/**
 * Utilities for UI tests.
 */

"use strict";

let {Builder, WebElementCondition} = require("selenium-webdriver");

/**
 * Start a WebDriver session for running the given Mocha *test*.
 *
 * *subject* is a text included in the subject of remote tests.
 */
exports.startBrowser = function(test, subject) {
    let webdriverURL = process.env.WEBDRIVER_URL || null;
    let tag = process.env.SUBJECT ? ` [${process.env.SUBJECT}]` : "";
    let capabilities = {
        browserName: process.env.BROWSER || "firefox",
        platform: process.env.PLATFORM,
        tunnelIdentifier: process.env.TUNNEL_ID,
        name: `[${subject}]${tag} ${test.fullTitle()}`
    };
    let browser = new Builder().usingServer(webdriverURL).withCapabilities(capabilities).build();
    browser.remote = Boolean(webdriverURL);
    return browser;
};

/**
 * Creates a condition that will loop until an element containing *text* is found by *locator*.
 */
exports.untilElementTextLocated = function(locator, text) {
    let msg = `for element containing "${text}" to be located by ${JSON.stringify(locator)}`;
    return new WebElementCondition(msg, async browser => {
        let elem;
        try {
            elem = await browser.findElement(locator);
        } catch (e) {
            return null;
        }
        let t = await elem.getText();
        return t.includes(text) ? elem : null;
    });
};
