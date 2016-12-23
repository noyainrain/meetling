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

/**
 * Meetling UI.
 */

"use strict";

var meetling = {};

meetling._DATE_TIME_FORMAT = {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
    hour: "numeric",
    minute: "numeric"
};

meetling._DATE_FORMAT = {year: "numeric", month: "long", day: "numeric"};

/**
 * Input for entering a time of day.
 *
 * The element implements the core functionality of a
 * `HTML time input <https://html.spec.whatwg.org/multipage/forms.html#time-state-%28type=time%29>`
 * . Be aware that *value* holds the user input, while *timeValue* holds the value as time string.
 *
 * .. attribute:: timeValue
 *
 *    Value as time string. Empty if the user input is invalid or empty.
 */
meetling.TimeInput = document.registerElement("meetling-time-input",
        {extends: "input", prototype: Object.create(HTMLInputElement.prototype, {
    // NOTE: Instead of introducing a new property *timeValue*, a better approach would be to
    // override *value*. We should refactor according to the comments below, as soon as current
    // browsers expose getters and setters of :class:`Node` s.

    createdCallback: {value: function() {
        this.classList.add("meetling-time-input");
        this.setAttribute("size", "5");
        this.addEventListener("change", this);
        this._value = null;
        // Better:
        //this._superValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
        this._evaluate();
    }},

    // Better: value: {
    timeValue: {
        get: function() {
            return this._value;
        },
        set: function(value) {
            this._value = this._parseInput(value);
            this.value = this._value;
            // Better: this._superValue.set.call(this, this._value);
            this.setCustomValidity("");
        }
    },

    handleEvent: {value: function(event) {
        if (event.currentTarget === this && event.type === "change") {
            this._evaluate();
        }
    }},

    _evaluate: {value: function() {
        var input = this.value;
        // Better: var input = this._superValue.get.call(this);
        this._value = this._parseInput(input);
        if (this._value || !input) {
            this.setCustomValidity("");
        } else {
            this.setCustomValidity("input_bad_format");
        }
    }},

    _parseInput: {value: function(input) {
        var tokens = input.match(/^([0-1]?\d|2[0-3])(\D?([0-5]\d))?$/);
        if (!tokens) {
            return "";
        }

        var hour = tokens[1];
        if (hour.length == 1) {
            hour = "0" + hour;
        }
        var minute = tokens[3] || "00";
        return hour + ":" + minute;
    }}
})});

/**
 * User element.
 *
 * .. attribute:: user
 *
 *    Represented :ref:`User`. Initialized from the JSON value of the corresponding HTML attribute,
 *    if present.
 */
meetling.UserElement = document.registerElement("meetling-user",
        {prototype: Object.create(HTMLElement.prototype, {
    createdCallback: {value: function() {
        this._user = null;
        this.appendChild(document.importNode(
            document.querySelector('.meetling-user-template').content, true));
        this.classList.add("meetling-user");
    }},

    user: {
        get: function() {
            return this._user;
        },
        set: function(value) {
            this._user = value;
            if (this._user) {
                this.querySelector("span").textContent = this._user.name;
                this.setAttribute("title", this._user.name);
            }
        }
    }
})});

/**
 * Compact listing of users.
 *
 * .. attribute:: users
 *
 *    List of :ref:`User` s to display. Initialized from the JSON value of the corresponding HTML
 *    attribute, if present.
 */
meetling.UserListingElement = document.registerElement("meetling-user-listing",
        {prototype: Object.create(HTMLElement.prototype, {
    createdCallback: {value: function() {
        this._users = [];
        this.classList.add("meetling-user-listing");
    }},

    users: {
        get: function() {
            return this._users;
        },
        set: function(value) {
            this._users = value;
            this.innerHTML = "";
            for (var i = 0; i < this._users.length; i++) {
                var user = this._users[i];
                if (i > 0) {
                    this.appendChild(document.createTextNode(", "));
                }
                var elem = document.createElement("meetling-user");
                elem.user = user;
                this.appendChild(elem);
            }
        }
    }
})});

/**
 * Meetling UI.
 *
 * .. attribute:: user
 *
 *    Current :ref:`User`.
 *
 * .. attribute:: settings
 *
 *    App :ref:`Settings`.
 */
meetling.UI = document.registerElement('meetling-ui',
        {extends: 'body', prototype: Object.create(micro.UI.prototype, {
    update: {value: function() {
        var version = localStorage.version || null;
        if (!version) {
            // Compatibility for server side authentication (obsolete since 0.10.0)
            return micro.call('POST', '/replace-auth').then(function(user) {
                this._storeUser(user);
                localStorage.version = 1;
            }.bind(this));
        }
    }},

    init: {value: function() {
        this.user = JSON.parse(localStorage.user);
        this.settings = null;

        this.pages = this.pages.concat([
            {url: '^/$', page: 'meetling-start-page'},
            {url: '^/about$', page: 'meetling-about-page'},
            {url: '^/create-meeting$', page: 'meetling-edit-meeting-page'},
            {url: '^/(?:users/([^/]+)|user)/edit$', page: this._makeEditUserPage.bind(this)},
            {url: '^/settings/edit$', page: this._makeEditSettingsPage.bind(this)},
            {url: '^/meetings/([^/]+)$', page: this._makeMeetingPage.bind(this)},
            {url: '^/meetings/([^/]+)/edit$', page: this._makeEditMeetingPage.bind(this)}
        ]);

        Object.assign(this.renderEvent, {
            'create-meeting': event => {
                var a = document.createElement('a');
                a.classList.add('link');
                a.href = `/meetings/${event.detail.meeting.id}`;
                a.textContent = event.detail.meeting.title;
                var userElem = document.createElement('meetling-user');
                userElem.user = event.user;
                return micro.util.formatFragment('{meeting} was created by {user}',
                                                 {meeting: a, user: userElem});
            }
        });

        window.addEventListener('error', this);
        this.addEventListener('user-edit', this);
        this.addEventListener('settings-edit', this);

        return Promise.resolve().then(function() {
            // If requested, log in with code
            var match = /^#login=(.+)$/.exec(location.hash);
            if (match) {
                history.replaceState(null, null, location.pathname);
                return micro.call('POST', '/api/login', {
                    code: match[1]
                }).then(this._storeUser.bind(this), function(e) {
                    // Ignore invalid login codes
                    if (!(e instanceof micro.APIError)) {
                        throw e;
                    }
                });
            }

        }.bind(this)).then(function() {
            // If not logged in (yet), log in as a new user
            if (!this.user) {
                return micro.call('POST', '/api/login').then(this._storeUser.bind(this));
            }

        }.bind(this)).then(function() {
            return micro.call('GET', '/api/settings');

        }).then(function(settings) {
            this.settings = settings;
            this._update();

            // Update the user details
            micro.call('GET', `/api/users/${this.user.id}`).then(function(user) {
                this.dispatchEvent(new CustomEvent('user-edit', {detail: {user: user}}));
            }.bind(this));

        }.bind(this)).catch(function(e) {
            // Authentication errors are a corner case and happen only if a) the user has deleted
            // their account on another device or b) the database has been reset (during
            // development)
            // TODO: Move to global error handling once unhandledrejection and ErrorEvent.error are
            // available in supported browsers
            if (e instanceof micro.APIError && e.error.__type__ === 'AuthenticationError') {
                this._storeUser(null);
                location.reload()
            } else {
                throw e;
            }
        }.bind(this));
    }},

    /**
     * Is the current :attr:`user` a staff member?
     */
    staff: {
        get: function() {
            return this.settings.staff.map(function(s) { return s.id; }).indexOf(this.user.id) !=
                   -1;
        }
    },

    /**
     * Show a *notification* to the user.
     *
     * *notification* is a :class:`HTMLElement`, like for example :class:`SimpleNotification`.
     * Alternatively, *notification* can be a simple message string to display.
     */
    notify: {value: function(notification) {
        if (typeof notification === "string") {
            var elem = document.createElement("meetling-simple-notification");
            var p = document.createElement("p");
            p.textContent = notification;
            elem.content.appendChild(p);
            notification = elem;
        }

        var space = this.querySelector('.meetling-ui-notification-space');
        space.textContent = "";
        space.appendChild(notification);
    }},

    synthesizeMeetingTrashAgendaItemEvent: {value: function(item) {
        var item = Object.assign({}, item, {trashed: true});
        this.dispatchEvent(new CustomEvent('trash-agenda-item', {detail: {item: item}}));
    }},

    _update: {value: function() {
        document.title = this.settings.title;
        this.classList.toggle('meetling-ui-user-is-staff', this.staff)
        this.classList.toggle('meetling-ui-settings-have-feedback-url', this.settings.feedback_url);
        this.querySelector('.meetling-ui-logo-text').textContent = this.settings.title;
        var img = this.querySelector('.meetling-ui-logo img');
        if (this.settings.favicon) {
            document.querySelector('link[rel="icon"]').href = this.settings.favicon;
            img.src = this.settings.favicon;
            img.style.display = '';
        } else {
            img.style.display = 'none';
        }
        this.querySelector('.meetling-ui-feedback a').href = this.settings.feedback_url;

        this.querySelector('.micro-ui-header meetling-user').user = this.user;
        this.querySelector('.meetling-ui-edit-settings').style.display = this.staff ? '' : 'none';
    }},

    _storeUser: {value: function(user) {
        this.user = user;
        if (user) {
            localStorage.user = JSON.stringify(user);
            document.cookie =
                `auth_secret=${user.auth_secret}; path=/; max-age=${360 * 24 * 60 * 60}`;
        } else {
            localStorage.user = null;
            document.cookie = 'auth_secret=; path=/; max-age=0';
        }
    }},

    _makeEditUserPage: {value: function(url, id) {
        id = id || this.user.id;
        return micro.call('GET', `/api/users/${id}`).then(function(user) {
            if (!(this.user.id === user.id)) {
                return document.createElement('micro-forbidden-page');
            }
            var page = document.createElement('meetling-edit-user-page');
            page.user = user;
            return page;
        }.bind(this));
    }},

    _makeEditSettingsPage: {value: function(url) {
        if (!this.staff) {
            return document.createElement('micro-forbidden-page');
        }
        return document.createElement('meetling-edit-settings-page');
    }},

    _makeMeetingPage: {value: function(url, id) {
        return micro.call('GET', `/api/meetings/${id}`).then(function(meeting) {
            var page = document.createElement('meetling-meeting-page');
            page.meeting = meeting;
            return page;
        });
    }},

    _makeEditMeetingPage: {value: function(url, id) {
        return micro.call('GET', `/api/meetings/${id}`).then(function(meeting) {
            var page = document.createElement('meetling-edit-meeting-page');
            page.meeting = meeting;
            return page;
        });
    }},

    handleEvent: {value: function(event) {
        micro.UI.prototype.handleEvent.call(this, event);

        if (event.currentTarget === window && event.type === "error") {
            this.notify(document.createElement("meetling-error-notification"));

            var type = "Error";
            var stack = `${event.filename}:${event.lineno}`;
            var message = event.message;
            // Get more detail out of ErrorEvent.error, if the browser supports it
            if (event.error) {
                type = event.error.name;
                stack = event.error.stack;
                message = event.error.message;
            }

            micro.call('POST', '/log-client-error', {
                type: type,
                stack: stack,
                url: location.pathname,
                message: message
            });

        } else if (event.target === this && event.type === 'user-edit') {
            this._storeUser(event.detail.user);
            this._update();

        } else if (event.target === this && event.type === 'settings-edit') {
            this.settings = event.detail.settings;
            this._update();
        }
    }}
})});

/**
 * Simple notification.
 */
meetling.SimpleNotification = document.registerElement("meetling-simple-notification",
        {prototype: Object.create(HTMLElement.prototype, {
    createdCallback: {value: function() {
        this.appendChild(document.importNode(
            ui.querySelector('.meetling-simple-notification-template').content, true));
        this.classList.add("meetling-notification", "meetling-simple-notification");
        this.querySelector(".meetling-simple-notification-dismiss").addEventListener("click", this);
        this.content = this.querySelector(".meetling-simple-notification-content");
    }},

    handleEvent: {value: function(event) {
        if (event.currentTarget === this.querySelector(".meetling-simple-notification-dismiss") &&
                event.type === "click") {
            this.parentNode.removeChild(this);
        }
    }}
})});

/**
 * Notification that informs the user about app errors.
 */
meetling.ErrorNotification = document.registerElement("meetling-error-notification",
        {prototype: Object.create(HTMLElement.prototype, {
    createdCallback: {value: function() {
        this.appendChild(document.importNode(
            ui.querySelector('.meetling-error-notification-template').content, true));
        this.classList.add("meetling-notification", "meetling-error-notification");
        this.querySelector(".meetling-error-notification-reload").addEventListener("click", this);
    }},

    handleEvent: {value: function(event) {
        if (event.currentTarget === this.querySelector(".meetling-error-notification-reload") &&
                event.type === "click") {
            location.reload();
        }
    }}
})});

/**
 * Start page.
 */
meetling.StartPage = class extends HTMLElement {
    createdCallback() {
        this.appendChild(document.importNode(
            ui.querySelector('.meetling-start-page-template').content, true));

        let img = this.querySelector('.meetling-logo img');
        if (ui.settings.icon) {
            img.src = ui.settings.icon;
            img.style.display = '';
        } else {
            img.style.display = 'none';
        }
        this.querySelector('.meetling-logo span').textContent = ui.settings.title;
        this.querySelector('.meetling-start-create-example-meeting').run =
            this._createExampleMeeting.bind(this);
    }

    _createExampleMeeting() {
        return micro.call('POST', '/api/create-example-meeting').then(meeting => {
            ui.navigate(`/meetings/${meeting.id}`);
        });
    }
}

/**
 * About page.
 */
meetling.AboutPage = document.registerElement('meetling-about-page',
        {prototype: Object.create(HTMLElement.prototype, {
    createdCallback: {value: function() {
        this.appendChild(document.importNode(
            ui.querySelector('.meetling-about-page-template').content, true));
        var h1 = this.querySelector('h1');
        h1.textContent = h1.dataset.text.replace('{title}', ui.settings.title);
        var p = this.querySelector('.meetling-about-short');
        p.textContent = p.dataset.text.replace('{title}', ui.settings.title);
    }}
})});

/**
 * Edit user page.
 */
meetling.EditUserPage = document.registerElement('meetling-edit-user-page',
        {prototype: Object.create(HTMLElement.prototype, {
    createdCallback: {value: function() {
        this._user = null;
        this.appendChild(document.importNode(
            ui.querySelector('.meetling-edit-user-page-template').content, true));
        this._form = this.querySelector('form');
        this.querySelector(".meetling-edit-user-edit").addEventListener("submit", this);

        this._setEmail1 = this.querySelector('.meetling-edit-user-set-email-1');
        this._setEmailForm = this.querySelector('.meetling-edit-user-set-email-1 form');
        this._setEmail2 = this.querySelector('.meetling-edit-user-set-email-2');
        this._emailP = this.querySelector('.meetling-edit-user-email-value');
        this._setEmailAction = this.querySelector('.meetling-edit-user-set-email-1 form button');
        this._cancelSetEmailAction = this.querySelector('.meetling-edit-user-set-email-2 button');
        this._removeEmailAction = this.querySelector('.meetling-edit-user-remove-email button');
        this._removeEmailAction.addEventListener('click', this);
        this._setEmailAction.addEventListener('click', this);
        this._cancelSetEmailAction.addEventListener('click', this);
        this._setEmailForm.addEventListener('submit', function(e) { e.preventDefault(); });
    }},

    attachedCallback: {value: function() {
        var match = /^#set-email=([^:]+):([^:]+)$/.exec(location.hash);
        if (match) {
            history.replaceState(null, null, location.pathname);
            var authRequestID = 'AuthRequest:' + match[1];
            var authRequest = JSON.parse(localStorage.authRequest || null);
            if (!authRequest || authRequestID != authRequest.id) {
                ui.notify(
                    'The email link was not opened on the same browser/device on which the email address was entered (or the email link is outdated).');
                return;
            }

            this._showSetEmailPanel2(true);
            micro.call('POST', `/api/users/${this._user.id}/finish-set-email`, {
                auth_request_id: authRequest.id,
                auth: match[2]
            }).then(function(user) {
                delete localStorage.authRequest;
                this.user = user;
                this._hideSetEmailPanel2();
            }.bind(this), function(e) {
                if (e.error.code === 'auth_invalid') {
                    this._showSetEmailPanel2();
                    ui.notify('The email link was modified. Please try again.');
                } else {
                    delete localStorage.authRequest;
                    this._hideSetEmailPanel2();
                    ui.notify({
                        auth_request_not_found: 'The email link is expired. Please try again.',
                        email_duplicate:
                            'The given email address is already in use by another user.'
                    }[e.error.code]);
                }
            }.bind(this));
        }
    }},

    /**
     * :ref:`User` to edit.
     */
    user: {
        get: function() {
            return this._user;
        },
        set: function(value) {
            this._user = value;
            this.classList.toggle('meetling-edit-user-has-email', this._user.email);
            this._form.elements['name'].value = this._user.name;
            this._emailP.textContent = this._user.email;
        }
    },

    _setEmail: {value: function() {
        if (!this._setEmailForm.checkValidity()) {
            return;
        }

        micro.call('POST', `/api/users/${this.user.id}/set-email`, {
            "email": this._setEmailForm.elements['email'].value
        }).then(function(authRequest) {
            localStorage.authRequest = JSON.stringify(authRequest);
            this._setEmailForm.reset();
            this._showSetEmailPanel2();
        }.bind(this));
    }},

    _cancelSetEmail: {value: function() {
        this._hideSetEmailPanel2();
    }},

    _removeEmail: {value: function() {
        micro.call('POST', `/api/users/${this.user.id}/remove-email`).then(function(user) {
            this.user = user;
        }.bind(this), function(e) {
            // If the email address has already been removed, we just update the UI
            this.user.email = null;
            this.user = this.user;
        }.bind(this));
    }},

    _showSetEmailPanel2: {value: function(progress) {
        progress = progress || false;
        var progressP = this.querySelector('.meetling-edit-user-set-email-2 .micro-progress');
        var actions = this.querySelector('.meetling-edit-user-set-email-2 .actions');
        this._emailP.style.display = 'none';
        this._setEmail1.style.display = 'none';
        this._setEmail2.style.display = 'block';
        if (progress) {
            progressP.style.display = '';
            actions.style.display = 'none';
        } else {
            progressP.style.display = 'none';
            actions.style.display = '';
        }
    }},

    _hideSetEmailPanel2: {value: function() {
        this._emailP.style.display = '';
        this._setEmail1.style.display = '';
        this._setEmail2.style.display = '';
    }},

    handleEvent: {value: function(event) {
        if (event.currentTarget === this._form) {
            event.preventDefault();
            micro.call('POST', `/api/users/${this._user.id}`, {
                name: this._form.elements['name'].value
            }).then(function(user) {
                ui.dispatchEvent(new CustomEvent('user-edit', {detail: {user: user}}));
            }, function(e) {
                if (e instanceof micro.APIError) {
                    ui.notify('The name is missing.');
                } else {
                    throw e;
                }
            }.bind(this));

        } else if (event.currentTarget === this._setEmailAction && event.type === 'click') {
            this._setEmail();
        } else if (event.currentTarget === this._cancelSetEmailAction && event.type === 'click') {
            this._cancelSetEmail();
        } else if (event.currentTarget === this._removeEmailAction && event.type === 'click') {
            this._removeEmail();
        }
    }}
})});

/**
 * Edit settings page.
 */
meetling.EditSettingsPage = document.registerElement('meetling-edit-settings-page',
        {prototype: Object.create(HTMLElement.prototype, {
    createdCallback: {value: function() {
        this.appendChild(document.importNode(
            ui.querySelector('.meetling-edit-settings-page-template').content, true));
        this._form = this.querySelector('form');
        this._form.elements['title'].value = ui.settings.title;
        this._form.elements['icon'].value = ui.settings.icon || '';
        this._form.elements['favicon'].value = ui.settings.favicon || '';
        this._form.elements['feedback_url'].value = ui.settings.feedback_url || '';
        this.querySelector('.meetling-edit-settings-edit').addEventListener('submit', this);
    }},

    attachedCallback: {value: function() {
        this._form.elements['title'].focus();
    }},

    handleEvent: {value: function(event) {
        if (event.currentTarget === this._form) {
            event.preventDefault();
            // Cancel submit if validation fails (not all browsers do this automatically)
            if (!this._form.checkValidity()) {
                return;
            }

            micro.call('POST', '/api/settings', {
                title: this._form.elements['title'].value,
                icon: this._form.elements['icon'].value,
                favicon: this._form.elements['favicon'].value,
                feedback_url: this._form.elements['feedback_url'].value
            }).then(function(settings) {
                ui.navigate('/');
                ui.dispatchEvent(new CustomEvent('settings-edit', {detail: {settings: settings}}));
            }.bind(this));
        }
    }}
})});

/**
 * Meeting page.
 */
meetling.MeetingPage = document.registerElement('meetling-meeting-page',
        {prototype: Object.create(HTMLElement.prototype, {
    createdCallback: {value: function() {
        this._meeting = null;

        this.appendChild(document.importNode(
            ui.querySelector('.meetling-meeting-page-template').content, true));
        this._agendaUl = this.querySelector(".meetling-meeting-agenda > ul");
        this._itemsOL = this.querySelector('.meetling-meeting-items > ol');
        this._trashedItemsUl = this.querySelector(".meetling-meeting-trashed-items > ul");
        this._showTrashedItemsAction = this.querySelector(".meetling-meeting-show-trashed-items");
        this._hideTrashedItemsAction = this.querySelector(".meetling-meeting-hide-trashed-items");
        this._createAgendaItemAction =
            this.querySelector(".meetling-meeting-create-agenda-item .action");
        this._shareAction = this.querySelector(".meetling-meeting-share");

        this._itemsOL.addEventListener('moveitem', this);
        this._showTrashedItemsAction.addEventListener("click", this);
        this._hideTrashedItemsAction.addEventListener("click", this);
        this._createAgendaItemAction.addEventListener("click", this);
        this._shareAction.addEventListener("click", this);
    }},

    attachedCallback: {value: function() {
        ui.addEventListener('trash-agenda-item', this);
        ui.addEventListener('restore-agenda-item', this);

        var p1 = micro.call('GET', `/api/meetings/${this._meeting.id}/items`);
        var p2 = micro.call('GET', `/api/meetings/${this._meeting.id}/items/trashed`);
        Promise.all([p1, p2]).then(function(results) {
            for (var item of results[0]) {
                var li = document.createElement('li', 'meetling-agenda-item');
                li.item = item;
                this._itemsOL.appendChild(li);
            }
            for (var item of results[1]) {
                var li = document.createElement('li', 'meetling-agenda-item');
                li.item = item;
                this._trashedItemsUl.appendChild(li);
            }
            this._update();
        }.bind(this));
    }},

    detachedCallback: {value: function() {
        ui.removeEventListener('trash-agenda-item', this);
        ui.removeEventListener('restore-agenda-item', this);
    }},

    /**
     * Represented :ref:`Meeting`.
     */
    meeting: {
        get: function() {
            return this._meeting;
        },
        set: function(value) {
            this._meeting = value;
            this.querySelector('h1').textContent = this._meeting.title;
            if (this._meeting.time) {
                var time = this.querySelector('.meetling-meeting-time time');
                time.dateTime = this._meeting.time;
                time.textContent = new Date(this._meeting.time).toLocaleString(
                    'en', meetling._DATE_TIME_FORMAT);
            } else {
                this.querySelector('.meetling-meeting-time').style.display = 'none';
            }
            if (this._meeting.location) {
                this.querySelector('.meetling-meeting-location span').textContent =
                    this._meeting.location;
            } else {
                this.querySelector('.meetling-meeting-location').style.display = 'none';
            }
            this.querySelector('.micro-multiline').textContent =
                this._meeting.description || '';
            this.querySelector('.meetling-detail meetling-user-listing').users =
                this._meeting.authors;
            this.querySelector('.meetling-meeting-edit').href =
                `/meetings/${this._meeting.id}/edit`;
            this._update();
        }
    },

    _update: {value: function() {
        var trashedItemsCoverLi = this.querySelector(".meetling-meeting-trashed-items-cover");
        var trashedItemsLi = this.querySelector(".meetling-meeting-trashed-items");
        var trashedItemElems = trashedItemsLi.querySelectorAll(".meetling-agenda-item");
        var span = trashedItemsCoverLi.querySelector("span");
        span.textContent =
            span.dataset.text.split("|")[trashedItemElems.length === 1 ? 0 : 1].replace("{n}",
                trashedItemElems.length);
        trashedItemsCoverLi.style.display = trashedItemElems.length ? "" : "none";
        trashedItemsLi.style.display = trashedItemElems.length ? "" : "none";
    }},

    _getAgendaItemElement: {value: function(id) {
        var elems = this.querySelectorAll(".meetling-meeting-agenda .meetling-agenda-item");
        for (var i = 0; i < elems.length; i++) {
            var li = elems[i];
            if (li.item.id === id) {
                return li;
            }
        }
        return null;
    }},

    _moveAgendaItem: {value: function(item, to) {
        return micro.call('POST', `/api/meetings/${this.meeting.id}/move-agenda-item`, {
            item_id: item.id,
            to_id: to ? to.id : null
        }).catch(function(e) {
            if (e instanceof micro.APIError && e.error.__type__ === 'ValueError' &&
                    e.error.code === 'item_not_found') {
                ui.synthesizeMeetingTrashAgendaItemEvent(item);
            } else if (e instanceof micro.APIError && e.error.__type__ === 'ValueError' &&
                       e.error.code === 'to_not_found') {
                // If the reference item has been trashed, retry by moving to its predecessor
                var previous = this._getAgendaItemElement(to.id).previousElementSibling;
                if (previous) {
                    previous = previous.item;
                }
                ui.synthesizeMeetingTrashAgendaItemEvent(to);
                return this._moveAgendaItem(item, previous);
            } else {
                throw e;
            }
        }.bind(this));
    }},

    handleEvent: {value: function(event) {
        if (event.target === ui && event.type === 'trash-agenda-item') {
            var li = this._getAgendaItemElement(event.detail.item.id);
            li.item = event.detail.item;
            this._trashedItemsUl.appendChild(li);
            this._update();

        } else if (event.target === ui && event.type === 'restore-agenda-item') {
            var li = this._getAgendaItemElement(event.detail.item.id);
            li.item = event.detail.item;
            this._itemsOL.appendChild(li);
            this._update();

        } else if (event.currentTarget === this._itemsOL && event.type === 'moveitem') {
            var to = event.detail.li.previousElementSibling;
            if (to) {
                to = to.item;
            }
            this._moveAgendaItem(event.detail.li.item, to);

        } else if ((event.currentTarget === this._showTrashedItemsAction ||
                    event.currentTarget === this._hideTrashedItemsAction) &&
                event.type === "click") {
            this._agendaUl.classList.toggle("meetling-meeting-agenda-trashed-items-visible");

        } else if (event.currentTarget === this._createAgendaItemAction && event.type === "click") {
            var li = this.querySelector(".meetling-meeting-create-agenda-item");
            var editor = new meetling.AgendaItemEditor();
            editor.replaced = li;
            this._agendaUl.insertBefore(editor, li);
            this._agendaUl.removeChild(li);

        } else if (event.currentTarget === this._shareAction && event.type === "click") {
            var notification = document.createElement("meetling-simple-notification");
            notification.content.appendChild(document.importNode(
                ui.querySelector('.meetling-share-notification-template').content, true));
            notification.content.querySelector("input").value =
                `${location.origin}/meetings/${this.meeting.id}`;
            ui.notify(notification);
        }
    }}
})});

/**
 * Edit meeting page.
 */
meetling.EditMeetingPage = document.registerElement('meetling-edit-meeting-page',
        {prototype: Object.create(HTMLElement.prototype, {
    createdCallback: {value: function() {
        this.appendChild(document.importNode(
            ui.querySelector('.meetling-edit-meeting-page-template').content, true));
        this._form = this.querySelector('.meetling-edit-meeting-edit');
        this.querySelector(".meetling-edit-meeting-example-date").textContent =
            new Date().toLocaleDateString("en", meetling._DATE_FORMAT);
        this.querySelector(".meetling-edit-meeting-edit").addEventListener("submit", this);

        this._pikaday = new Pikaday({
            field: this.querySelector('.meetling-edit-meeting-edit [name="date"]'),
            firstDay: 1,
            numberOfMonths: 1,
            onDraw: this._onDrawPikaday.bind(this)
        });
        this._pikaday.toString = this._formatDate.bind(this);
        this._clearButton = document.createElement("button");
        this._clearButton.classList.add("pika-clear");
        this._clearButton.textContent = "Clear";
        this._clearButton.addEventListener("click", this);
        // Pikaday prevents click events on touch-enabled devices
        this._clearButton.addEventListener("touchend", this);

        this.meeting = null;
    }},

    attachedCallback: {value: function() {
        this._form.elements['title'].focus();
    }},

    /**
     * :ref:`Meeting` to edit.
     *
     * ``null`` means the page is in create mode.
     */
    meeting: {
        get: function() {
            return this._meeting;
        },
        set: function(value) {
            this._meeting = value;
            var h1 = this.querySelector('h1');
            var action = this.querySelector('.action-cancel');
            if (this._meeting) {
                h1.textContent = `Edit ${this._meeting.title}`;
                this._form.elements['title'].value = this._meeting.title;
                if (this._meeting.time) {
                    var time = new Date(this.meeting.time);
                    this._pikaday.setDate(time);
                    var hour = time.getHours();
                    var minute = time.getMinutes();
                    this._form.elements['time'].timeValue =
                        `${hour < 10 ? '0' + hour : hour}:${minute < 10 ? '0' + minute : minute}`;
                }
                this._form.elements['location'].value = this._meeting.location || '';
                this._form.elements['description'].value = this._meeting.description || '';
                action.href = `/meetings/${this._meeting.id}`;
            } else {
                h1.textContent = 'New Meeting';
                action.href = `/`;
            }
        }
    },

    _formatDate: {value: function() {
        return this._pikaday.getDate().toLocaleDateString("en", meetling._DATE_FORMAT);
    }},

    _onDrawPikaday: {value: function() {
        this._pikaday.el.appendChild(this._clearButton);
    }},

    handleEvent: {value: function(event) {
        if (event.currentTarget === this._form && event.type === 'submit') {
            event.preventDefault();

            var dateTime = null;
            var date = this._pikaday.getDate();
            var time = this._form.elements['time'].timeValue;
            if (date || time || !this._form.elements['time'].checkValidity()) {
                if (!(date && time)) {
                    ui.notify('Date and time are incomplete.');
                    return;
                }
                dateTime = date;
                var tokens = time.split(":");
                dateTime.setHours(parseInt(tokens[0]), parseInt(tokens[1]));
                dateTime = dateTime.toISOString();
            }

            var url = '/api/meetings';
            if (this.meeting) {
                url = `/api/meetings/${this.meeting.id}`;
            }

            micro.call('POST', url, {
                title: this._form.elements['title'].value,
                time: dateTime,
                location: this._form.elements['location'].value,
                description: this._form.elements['description'].value
            }).then(function(meeting) {
                ui.navigate(`/meetings/${meeting.id}`);
            }, function(e) {
                if (e instanceof micro.APIError) {
                    ui.notify('The title is missing.');
                } else {
                    throw e;
                }
            }.bind(this));

        } else if (event.currentTarget === this._clearButton && (event.type === "click" ||
                                                                 event.type === "touchend")) {
            this._pikaday.setDate(null);
            this._pikaday.hide();
        }
    }}
})});

/**
 * Agenda item element.
 *
 * .. attribute:: item
 *
 *    Represented :ref:`AgendaItem`. The initial value is set from the JSON value of the HTML
 *    attribute of the same name.
 */
meetling.AgendaItemElement = document.registerElement("meetling-agenda-item",
        {extends: "li", prototype: Object.create(HTMLLIElement.prototype, {
    createdCallback: {value: function() {
        this._item = null;
        this.appendChild(document.importNode(
            ui.querySelector('.meetling-agenda-item-template').content, true));
        this.classList.add("meetling-agenda-item");
        this._trashAction = this.querySelector(".meetling-agenda-item-trash");
        this._restoreAction = this.querySelector(".meetling-agenda-item-restore");
        this._trashAction.addEventListener("click", this);
        this._restoreAction.addEventListener("click", this);
        this.querySelector(".meetling-agenda-item-edit").addEventListener("click", this);
    }},

    item: {
        get: function() {
            return this._item;
        },
        set: function(value) {
            this._item = value;
            if (this._item) {
                this.classList.toggle("meetling-agenda-item-trashed", this._item.trashed);
                this.querySelector("h1").textContent = this._item.title;
                var p = this.querySelector(".meetling-agenda-item-duration");
                if (this._item.duration) {
                    p.querySelector("span").textContent = this._item.duration + "m";
                    p.style.display = "";
                } else {
                    p.style.display = "none";
                }
                this.querySelector(".meetling-agenda-item-description").textContent =
                    this._item.description || "";
                this.querySelector("meetling-user-listing").users = this._item.authors;
            }
        }
    },

    handleEvent: {value: function(event) {
        if (event.currentTarget === this.querySelector(".meetling-agenda-item-edit")) {
            var editor = new meetling.AgendaItemEditor();
            editor.item = this._item;
            editor.replaced = this;
            this.parentNode.insertBefore(editor, this);
            this.parentNode.removeChild(this);

        } else if (event.currentTarget === this._trashAction && event.type === "click") {
            micro.call('POST', `/api/meetings/${ui.page.meeting.id}/trash-agenda-item`, {
                item_id: this._item.id
            }).catch(function(e) {
                // If the item has already been trashed, we continue as normal to update the UI
                if (!(e instanceof micro.APIError && e.error.__type__ === 'ValueError' &&
                      e.error.code === 'item_not_found')) {
                    throw e;
                }
            }).then(function() {
                ui.synthesizeMeetingTrashAgendaItemEvent(this._item);
            }.bind(this));

        } else if (event.currentTarget === this._restoreAction && event.type === "click") {
            micro.call('POST', `/api/meetings/${ui.page.meeting.id}/restore-agenda-item`, {
                item_id: this._item.id
            }).catch(function(e) {
                // If the item has already been restored, we continue as normal to update the UI
                if (!(e instanceof micro.APIError && e.error.__type__ === 'ValueError' &&
                      e.error.code === 'item_not_found')) {
                    throw e;
                }
            }).then(function() {
                this._item.trashed = false;
                ui.dispatchEvent(
                    new CustomEvent('restore-agenda-item', {detail: {item: this._item}}));
            }.bind(this));
        }
    }}
})});

/**
 * Agenda item editor.
 *
 * .. attribute:: item
 *
 *    :ref:`AgendaItem` to edit. ``null`` means the editor is in create mode.
 *
 * .. attribute:: replaced
 *
 *    ``li`` that was temporarily replaced with the editor.
 */
meetling.AgendaItemEditor = document.registerElement("meetling-agenda-item-editor",
        {extends: "li", prototype: Object.create(HTMLLIElement.prototype, {
    createdCallback: {value: function() {
        this.appendChild(document.importNode(
            ui.querySelector('.meetling-agenda-item-editor-template').content, true));
        this.classList.add("meetling-agenda-item-editor");
        this.querySelector('.action').run = this._edit.bind(this);
        this.querySelector('.action-cancel').run = this._close.bind(this);
        this.item = null;
        this.replaced = null;
    }},

    attachedCallback: {value: function() {
        this.querySelector("form").elements["title"].focus();
    }},

    item: {
        get: function() {
            return this._item;
        },
        set: function(value) {
            this._item = value;
            if (this._item) {
                this.querySelector('h1').textContent = "Edit " + this._item.title;
                var form = this.querySelector("form");
                form.elements["title"].value = this._item.title;
                form.elements["duration"].value = this._item.duration || "";
                form.elements["description"].value = this._item.description || "";
            }
        }
    },

    _edit: {value: function() {
        let form = this.querySelector('form');

        if (!form.elements['duration'].checkValidity()) {
            ui.notify('Duration is not a number.');
            return;
        }

        var url = `/api/meetings/${ui.page.meeting.id}/items`;
        if (this._item) {
            url = `/api/meetings/${ui.page.meeting.id}/items/${this._item.id}`;
        }

        return micro.call('POST', url, {
            title: form.elements['title'].value,
            duration: form.elements['duration'].value ?
                parseInt(form.elements['duration'].value) : null,
            description: form.elements['description'].value
        }).then(item => {
            if (this._item) {
                // In edit mode, update the corresponding meetling-agenda-item
                this.replaced.item = item;
            } else {
                // In create mode, append a new meetling-agenda-item to the list
                let li = new meetling.AgendaItemElement();
                li.item = item;
                this.parentNode.querySelector('.meetling-meeting-items > ol').appendChild(li);
            }
            this._close();
        }, e => {
            if (e instanceof micro.APIError && e.error.__type__ === 'InputError') {
                let arg = Object.keys(e.error.errors)[0];
                ui.notify({
                    title: {empty: 'Title is missing.'},
                    duration: {not_positive: 'Duration is not positive.'}
                }[arg][e.error.errors[arg]]);
            } else {
                throw e;
            }
        });
    }},

    _close: {value: function() {
        this.parentNode.insertBefore(this.replaced, this);
        this.parentNode.removeChild(this);
    }}
})});

document.registerElement('meetling-start-page', meetling.StartPage);
