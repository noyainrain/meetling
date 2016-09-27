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
var SMTPServer = require('smtp-server').SMTPServer;

var WebAPIClient = require('../micro/webapi').WebAPIClient;

var TIMEOUT = 1000;

describe('UI scenarios', function() {
    this.timeout(5 * 60 * 1000);

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
        server = spawn('python3', ['-m', 'meetling', '--smtp-url', '//localhost:2525']);
        server.on('err', err => {
            throw err;
        });

        // make test-ui SELENIUM_REMOTE_URL="https://{user}:{key}@ondemand.saucelabs.com:443/wd/hub" PLATFORM="OS X 10.11"
        browser = process.env.BROWSER || 'firefox';
        var platform = process.env.PLATFORM || null;
        browser = new Builder().withCapabilities({browserName: browser, platform: platform, marionette: true}).build();
    });

    afterEach(function() {
        if (server) {
            server.kill();
        }

        if (browser) {
            return browser.quit();
        }
    });

    xit('User creates meeting', function() {
        // Start to create meeting
        // TODO: Either use Sauce Connect or TUNNEL env variable
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

    it('User subscribes to meeting', function() {
        var mailboxes = {};
        var server = new SMTPServer({
            disabledCommands: ['AUTH'],
            onData: function(stream, session, callback) {
                var mail = '';
                stream.setEncoding('utf8');
                stream.on('data', data => {
                    mail += data;
                });
                stream.on('end', () => {
                    for (var rcptTo of session.envelope.rcptTo) {
                        if (!(rcptTo.address in mailboxes)) {
                            mailboxes[rcptTo.address] = [];
                        }
                        mailboxes[rcptTo.address].push(mail);
                    }
                    callback();
                });
            }
        }).listen(2525);

        /*simplesmtp.createSimpleServer({}, function(req) {
            req.pipe(process.stdout);
            req.accept();
            done();
        }).listen(2222);*/

        browser.get('http://localhost:8080/');

        //browser.wait(until.elementLocated({css: '.micro-ui-header meetling-user'}), TIMEOUT).click();
        browser.wait(until.elementLocated({css: '.meetling-ui-menu button.link'}), TIMEOUT).click();
        browser.findElement({css: '.meetling-ui-edit-user'}).click();

        var form = browser.wait(until.elementLocated({css: 'meetling-edit-user-page form'}), TIMEOUT);
        var nameInput = form.findElement({name: 'name'});
        nameInput.clear();
        nameInput.sendKeys('Grumpy');
        form.findElement({css: 'button'}).click();

        form = browser.findElement({css: '.meetling-edit-user-set-email-1'});
        form.findElement({name: 'email'}).sendKeys('foo@example.org');
        form.findElement({css: 'button'}).click();

        browser.wait(() => 'foo@example.org' in mailboxes, TIMEOUT).then(() => {
            var mailbox = mailboxes['foo@example.org'];
            var match = /^http.+$/m.exec(mailbox[0]);
            browser.get(match[0]);
        });

        browser.findElement({css: '.meetling-ui-logo'}).click();

        var button = browser.wait(until.elementLocated({css: '.meetling-start-create-example-meeting'}), TIMEOUT);
        button.click();

        browser.wait(until.elementLocated({css: 'meetling-meeting-page'}), TIMEOUT);

        var api = new WebAPIClient({url: 'http://localhost:8080/api'});
        var meetingID;
        var items;

        browser.getCurrentUrl().then(url => {
            meetingID = url.split('/').pop();
            return api.call('POST', '/login');
        }).then(user => {
            api.headers['Cookie'] = `auth_secret=${user.auth_secret}`;
            return api.call('POST', `/users/${user.id}`, {name: 'Hover'});
        }).then(() => {
            return api.call('GET', `/meetings/${meetingID}/items`);
        }).then(itms => {
            items = itms;
            return api.call('POST', `/meetings/${meetingID}`, {title: 'Management meeting'});
        }).then(() => {
            return api.call('POST', `/meetings/${meetingID}/items`, {title: 'Office decoration'});
        }).then(item => {
            items.push(item);
            return api.call('POST', `/meetings/${meetingID}/move-agenda-item`,
                            {item_id: items[3].id, to_id: items[1].id});
        }).then(() => {
            return api.call('POST', `/meetings/${meetingID}/trash-agenda-item`, {item_id: items[2].id});
        }).then(() => {
            return api.call('POST', `/meetings/${meetingID}/restore-agenda-item`, {item_id: items[2].id});
        }).then(() => {
            return api.call('POST', `/meetings/${meetingID}/items/${items[2].id}`, {duration: 10});
        });

        // Check mail
        var mailbox;
        browser.wait(() => mailboxes['foo@example.org'].length === 7, TIMEOUT).then(() => {
            mailbox = mailboxes['foo@example.org'];
            //console.log(mailbox);
            for (var mail of mailbox) {
                console.log(mail, '\n');
            }
            // In every notification: a) name of subscriber b) name of acting user c) meeting name
            // (feed)
            expect(mailbox[1]).to.contain('Grumpy').and.to.contain('Hover').match(/Management\s+meeting/);

            expect(mailbox[1]).to.contain('edited');
            expect(mailbox[2]).to.contain('proposed').and.match(/Office\s+decoration/);
            expect(mailbox[3]).to.contain('moved').and.match(/Office\s+decoration/);
            expect(mailbox[4]).to.contain('trashed').and.match(/Next\s+meeting/);
            expect(mailbox[5]).to.contain('restored').and.match(/Next\s+meeting/);
            expect(mailbox[6]).to.contain('edited').match(/Next\s+meeting/);
        });

        return browser.sleep(1);
    });
});
