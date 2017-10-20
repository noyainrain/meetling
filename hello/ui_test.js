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

/* eslint-env mocha, node */
/* eslint-disable no-invalid-this, prefer-arrow-callback */

"use strict";

let {exec, spawn} = require("child_process");
let {promisify} = require("util");

let {until} = require("selenium-webdriver");

let {startBrowser, untilElementTextLocated} = require("micro/test");

let URL = "http://localhost:8081";

describe("UI", function() {
    let server;
    let browser;
    let timeout;

    this.timeout(5 * 60 * 1000);

    beforeEach(async function() {
        await promisify(exec)("redis-cli -n 15 flushdb");
        server = spawn("python3", ["-m", "hello", "--port", "8081", "--redis-url", "15"],
                       {stdio: "inherit"});
        browser = startBrowser(this.currentTest, "micro");
        timeout = browser.remote ? 10 * 1000 : 1000;
    });

    afterEach(async function() {
        if (server) {
            server.kill();
        }
        if (browser) {
            await browser.quit();
        }
    });

    it("should work for a user", async function() {
        // View start page
        await browser.get(`${URL}/`);
        await browser.wait(
            untilElementTextLocated({css: ".micro-logo"}, "Hello"), timeout);

        // Create greeting
        let form = await browser.findElement({css: ".hello-start-create-greeting form"});
        let input = await form.findElement({name: "text"});
        await input.sendKeys("Meow!");
        await form.findElement({css: "button"}).click();
        await browser.wait(untilElementTextLocated({css: ".hello-greeting q"}, "Meow!"), timeout);

        // Edit user
        let menu = await browser.findElement({css: ".micro-ui-header-user"});
        await browser.actions().mouseMove(menu).perform();
        await browser.findElement({css: ".micro-ui-edit-user"}).click();
        await browser.wait(
            untilElementTextLocated({css: "micro-edit-user-page h1"}, "Edit user settings"),
            timeout);
        form = await browser.findElement({css: ".micro-edit-user-edit"});
        input = await form.findElement({name: "name"});
        await input.clear();
        await input.sendKeys("Happy");
        await form.findElement({css: "button"}).click();
        await browser.wait(
            until.elementTextContains(
                await browser.findElement({css: ".micro-ui-header micro-user"}),
                "Happy"),
            timeout);

        // View about page
        menu = await browser.findElement({css: ".micro-ui-header-menu"});
        await browser.actions().mouseMove(menu).perform();
        await browser.findElement({css: ".micro-ui-about"}).click();
        await browser.wait(
            untilElementTextLocated({css: "micro-about-page h1"}, "About Hello"), timeout);
    });

    it("should work for staff", async function() {
        // Edit site settings
        await browser.get(`${URL}/`);
        let menu = await browser.wait(until.elementLocated({css: ".micro-ui-header-menu"}),
                                      timeout);
        await browser.actions().mouseMove(menu).perform();
        await browser.findElement({css: ".micro-ui-edit-settings"}).click();
        await browser.wait(
            untilElementTextLocated({css: "micro-edit-settings-page h1"}, "Edit site settings"),
            timeout);
        let form = await browser.findElement({css: ".micro-edit-settings-edit"});
        let input = await form.findElement({name: "title"});
        await input.clear();
        await input.sendKeys("CatApp");
        await form.findElement({name: "icon"}).sendKeys("/static/images/icon.svg");
        await form.findElement({name: "favicon"}).sendKeys("/static/images/favicon.png");
        await form.findElement({name: "provider_name"}).sendKeys("Happy");
        await form.findElement({name: "provider_url"}).sendKeys("https://happy.example.org/");
        await form.findElement({name: "feedback_url"}).sendKeys("https://feedback.example.org/");
        await form.findElement({css: "button"}).click();
        await browser.wait(
            until.elementTextContains(await browser.findElement({css: ".micro-ui-logo"}),
                                      "CatApp"),
            timeout);

        // View activity page
        await browser.actions().mouseMove(menu).perform();
        await browser.findElement({css: ".micro-ui-activity"}).click();
        await browser.wait(
            untilElementTextLocated({css: "micro-activity-page .micro-timeline li"},
                                    "site settings"),
            timeout);
    });
});
