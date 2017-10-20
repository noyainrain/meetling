/*
 * Meetling
 * Copyright (C) 2017 Meetling contributors
 *
 * This program is free software: you can redistribute it and/or modify it under the terms of the
 * GNU General Public License as published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
 * even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along with this program. If
 * not, see <http://www.gnu.org/licenses/>.
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
        server = spawn("python3",
                       ["-m", "meetling", "--port", "8081", "--url", URL, "--redis-url", "15"],
                       {cwd: "..", stdio: "inherit"});
        browser = startBrowser(this.currentTest, "Meetling");
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
            untilElementTextLocated({css: ".micro-logo"}, "My Meetling"), timeout);

        // Create meeting
        await browser.findElement({css: ".meetling-start-create-meeting"}).click();
        let form = await browser.findElement({css: ".meetling-edit-meeting-edit"});
        await form.findElement({name: "title"}).sendKeys("Cat hangout");
        await form.findElement({name: "date"}).click();
        await browser.findElement({css: ".is-today .pika-day"}).click();
        await form.findElement({name: "time"}).sendKeys("13:30");
        await form.findElement({name: "description"}).sendKeys("Just hanging out.");
        await form.findElement({css: "button"}).click();
        await browser.wait(
            untilElementTextLocated({css: "meetling-meeting-page h1"}, "Cat hangout"), timeout);

        // Create example meeting
        await browser.findElement({css: ".micro-ui-logo"}).click();
        await browser.findElement({css: ".meetling-start-create-example-meeting"}).click();
        await browser.wait(
            untilElementTextLocated({css: "meetling-meeting-page h1"}, "Working group meeting"),
            timeout);

        // Edit meeting
        await browser.findElement({css: ".meetling-meeting-edit"}).click();
        await browser.wait(
            untilElementTextLocated({css: "meetling-edit-meeting-page h1"},
                                    "Edit Working group meeting"),
            timeout);
        form = await browser.findElement({css: ".meetling-edit-meeting-edit"});
        let input = await form.findElement({name: "title"});
        await input.clear();
        await input.sendKeys("Cat hangout");
        await form.findElement({css: "button"}).click();
        await browser.wait(
            untilElementTextLocated({css: "meetling-meeting-page h1"}, "Cat hangout"), timeout);

        // Create agenda item
        await browser.findElement({css: ".meetling-meeting-create-agenda-item button"}).click();
        form = await browser.findElement({css: ".meetling-agenda-item-editor-edit"});
        await form.findElement({name: "title"}).sendKeys("Purring");
        await form.findElement({name: "duration"}).sendKeys("10");
        await form.findElement({css: "button"}).click();
        await browser.wait(
            untilElementTextLocated({css: "[is=meetling-agenda-item]:last-child h1"}, "Purring"),
            timeout);

        // Edit agenda item
        await browser.findElement({css: ".meetling-agenda-item-edit"}).click();
        form = await browser.findElement({css: ".meetling-agenda-item-editor-edit"});
        input = await form.findElement({name: "title"});
        await input.clear();
        await input.sendKeys("Intro");
        await form.findElement({css: "button"}).click();
        await browser.wait(
            untilElementTextLocated({css: "[is=meetling-agenda-item] h1"}, "Intro"), timeout);

        // Trash agenda item
        await browser.findElement({css: ".meetling-agenda-item-menu .micro-menu-toggle-secondary"})
            .click();
        await browser.findElement({css: ".meetling-agenda-item-trash"}).click();
        await browser.wait(
            until.elementIsVisible(
                await browser.findElement({css: ".meetling-meeting-trashed-items-cover"})),
            timeout);

        // Restore agenda item
        await browser.findElement({css: ".meetling-meeting-show-trashed-items"}).click();
        await browser
            .findElement({css: ".meetling-meeting-trashed-items .meetling-agenda-item-restore"})
            .click();
        await browser.wait(
            untilElementTextLocated({css: "[is=meetling-agenda-item]:last-child h1"}, "Intro"),
            timeout);

        // View about page
        let menu = await browser.findElement({css: ".micro-ui-header-menu"});
        await browser.actions().mouseMove(menu).perform();
        await browser.findElement({css: ".micro-ui-about"}).click();
        await browser.wait(
            untilElementTextLocated({css: "micro-about-page h1"}, "About My Meetling"), timeout);
    });
});
