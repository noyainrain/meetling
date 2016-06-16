/*
 * Meetling
 * Copyright (C) 2015 Meetling contributors
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

'use strict';

var execSync = require('child_process').execSync;
var spawn = require('child_process').spawn;

var expect = require('chai').expect;
var Builder = require('selenium-webdriver').Builder;
var until = require('selenium-webdriver/lib/until');

var TIMEOUT = 1000;

describe('UI scenarios', function() {
    this.timeout(60 * 1000);

    var server;
    var browser;

    function createAgendaItem(title, options) {
        options = Object.assign({duration: null, description: null}, options);

        var selector = {css: '.meetling-meeting-items .meetling-agenda-item'};
        return browser.findElements(selector).then(items => {
            browser.findElement({css: '.meetling-meeting-create-agenda-item .action'}).click();
            var form = browser.findElement({css: '.meetling-agenda-item-editor form'});
            form.findElement({name: 'title'}).sendKeys(title);
            if (options.duration) {
                form.findElement({name: 'duration'}).sendKeys(options.duration);
            }
            if (options.description) {
                form.findElement({name: 'description'}).sendKeys(options.description);
            }
            form.findElement({css: 'button'}).click();
            selector = {css: `.meetling-meeting-items .meetling-agenda-item:nth-child(${items.length + 1}) h1`};
            return browser.wait(until.elementLocated(selector), TIMEOUT).getText();

        }).then(text => {
            expect(text).to.contain(title);
        });
    }

    beforeEach(function() {
        execSync('make sample');
        server = spawn('python3', ['-m', 'meetling']);
        server.on('err', err => {
            throw err;
        });

        browser = process.env.BROWSER || 'firefox';
        browser = new Builder().withCapabilities({browserName: browser, marionette: true}).build();
    });

    afterEach(function() {
        if (server) {
            server.kill();
        }

        if (browser) {
            return browser.quit();
        }
    });

    it('User creates meeting', function() {
        // Start to create meeting
        browser.get('http://localhost:8080/');
        browser.wait(until.elementLocated({css: '.meetling-start-create-meeting'}), TIMEOUT).click();

        // Create meeting
        var form = browser.findElement({css: '.meetling-edit-meeting-edit'});
        form.findElement({name: 'title'}).sendKeys('Cat hangout');
        form.findElement({name: 'date'}).click();
        browser.findElement({css: '.is-today .pika-day'}).click();
        form.findElement({name: 'time'}).sendKeys('13:30');
        form.findElement({name: 'location'}).sendKeys('Backyard');
        form.findElement({name: 'description'}).sendKeys('A good place for cats TODO.');
        form.findElement({css: 'button'}).click();
        var h1 = browser.wait(until.elementLocated({css: 'meetling-meeting-page h1'}), TIMEOUT);
        h1.getText().then(text => {
            expect(text).to.contain('Cat hangout');
        });

        // Create agenda items
        createAgendaItem('Eating');
        createAgendaItem('Purring', {duration: 10, description: 'No snooping!'});
        createAgendaItem('Napping');

        // Trash agenda item
        browser.findElement({css: '.meetling-agenda-item-menu .micro-menu-toggle-secondary'}).click();
        browser.findElement({css: '.meetling-agenda-item-trash'}).click();

        // Restore agenda item
        var showTrashedItemsButton = browser.findElement({css: '.meetling-meeting-show-trashed-items'});
        browser.wait(until.elementIsVisible(showTrashedItemsButton), TIMEOUT);
        showTrashedItemsButton.click();
        browser.findElement({css: '.meetling-meeting-trashed-items .meetling-agenda-item-restore'}).click();
        var h1 = browser.wait(until.elementLocated(
            {css: '.meetling-meeting-items .meetling-agenda-item:nth-child(3) h1'}), TIMEOUT);
        h1.getText().then(text => {
            expect(text).to.contain('Eating');
        });

        // Share
        browser.findElement({css: '.meetling-meeting-share'}).click();
        return browser.findElement({css: '.meetling-simple-notification-content'}).getText().then(text => {
            expect(text).to.contain('To share');
        });
    });
});
