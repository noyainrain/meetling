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
 * and can thus be used as a polyfill.
 */
meetling.TimeInput = document.registerElement("meetling-time-input",
        {extends: "input", prototype: Object.create(HTMLInputElement.prototype, {
    createdCallback: {value: function() {
        this.classList.add("meetling-time-input");
        this.setAttribute("size", "5");
        this.addEventListener("change", this);
        this._value = null;
        this._superValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
        this._evaluate();
    }},

    value: {
        get: function() {
            return this._value;
        },
        set: function(value) {
            this._value = this._parseInput(value);
            this._superValue.set.call(this, this._value);
            this.setCustomValidity("");
        }
    },

    handleEvent: {value: function(event) {
        if (event.currentTarget === this && event.type === "change") {
            this._evaluate();
        }
    }},

    _evaluate: {value: function() {
        var input = this._superValue.get.call(this);
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
        meetling.loadTemplate(this, ".meetling-user-template");
        this.classList.add("meetling-user");
        this.user = JSON.parse(this.getAttribute("user"));
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
        this.classList.add("meetling-user-listing");
        this.users = JSON.parse(this.getAttribute("users")) || [];
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
 * Meetling page.
 *
 * .. attribute:: user
 *
 *    Current :ref:`User`. Initialized from the JSON value of the corresponding HTML attribute.
 */
meetling.Page = document.registerElement("meetling-page",
        {extends: "body", prototype: Object.create(HTMLBodyElement.prototype, {
    createdCallback: {value: function() {
        window.addEventListener("error", this);
        this.user = JSON.parse(this.getAttribute("user"));
    }},

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
        this.querySelector(".meetling-page-notification-space").appendChild(notification);
    }},

    handleEvent: {value: function(event) {
        if (event.currentTarget === window && event.type === "error") {
            this.notify(document.createElement("meetling-error-notification"));
            var url = "/log-client-error";
            fetch(url, {method: "POST", credentials: "include", body: JSON.stringify({
                type: event.error.name,
                stack: event.error.stack,
                url: location.pathname,
                message: event.error.message
            })});
        }
    }}
})});

/**
 * Simple notification.
 */
meetling.SimpleNotification = document.registerElement("meetling-simple-notification",
        {prototype: Object.create(HTMLElement.prototype, {
    createdCallback: {value: function() {
        meetling.loadTemplate(this, ".meetling-simple-notification-template");
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
        meetling.loadTemplate(this, ".meetling-error-notification-template");
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
 * Start page, built on ``start.html``.
 */
meetling.StartPage = document.registerElement("meetling-start-page",
        {extends: "body", prototype: Object.create(meetling.Page.prototype, {
    createdCallback: {value: function() {
        meetling.Page.prototype.createdCallback.call(this);
        this.querySelector(".meetling-start-create-example-meeting").addEventListener("click",
                                                                                      this);
    }},

    handleEvent: {value: function(event) {
        meetling.Page.prototype.handleEvent.call(this, event);
        if (event.currentTarget === this.querySelector(".meetling-start-create-example-meeting")) {
            var request = new Request("/api/create-example-meeting",
                                      {method: "POST", credentials: "include"})
            fetch(request).then(function(response) {
                return response.json();
            }).then(function(meeting) {
                location.assign("/meetings/" + meeting.id);
            });
        }
    }}
})});

/**
 * Edit user page, built on ``edit-user.html``.
 *
 * .. attribute:: userObject
 *
 *    :ref:`User` to edit. Initialized from the JSON value of the corresponding HTML attribute.
 */
meetling.EditUserPage = document.registerElement("meetling-edit-user-page",
        {extends: "body", prototype: Object.create(meetling.Page.prototype, {
    createdCallback: {value: function() {
        meetling.Page.prototype.createdCallback.call(this);
        this.querySelector(".meetling-edit-user-edit").addEventListener("submit", this);
        this.userObject = JSON.parse(this.getAttribute("user-object"));
    }},

    handleEvent: {value: function(event) {
        meetling.Page.prototype.handleEvent.call(this, event);
        var form = this.querySelector(".meetling-edit-user-edit");
        if (event.currentTarget === form) {
            event.preventDefault();
            var url = "/api/users/" + this.userObject.id;
            fetch(url, {method: "POST", credentials: "include", body: JSON.stringify({
                name: form.elements["name"].value
            })}).then(function(response) {
                return response.json();
            }).then(function(user) {
                if (user.__type__ === "InputError") {
                    this.notify("The name is missing.");
                    return;
                }
                location.assign("/");
            }.bind(this));
        }
    }}
})});

/**
 * Edit settings page, built on ``edit-settings.html``.
 */
meetling.EditSettingsPage = document.registerElement("meetling-edit-settings-page",
        {extends: "body", prototype: Object.create(meetling.Page.prototype, {
    createdCallback: {value: function() {
        meetling.Page.prototype.createdCallback.call(this);
        this.querySelector(".meetling-edit-settings-edit").addEventListener("submit", this);
    }},

    handleEvent: {value: function(event) {
        meetling.Page.prototype.handleEvent.call(this, event);
        var form = this.querySelector(".meetling-edit-settings-edit");
        if (event.currentTarget === form) {
            event.preventDefault();
            fetch("/api/settings", {method: "POST", credentials: "include", body: JSON.stringify({
                title: form.elements["title"].value,
                icon: form.elements["icon"].value,
                favicon: form.elements["favicon"].value
            })}).then(function(response) {
                return response.json();
            }).then(function(settings) {
                if (settings.__type__ === "InputError") {
                    this.notify("The title is missing");
                    return;
                }
                location.assign("/");
            }.bind(this));
        }
    }}
})});

/**
 * Meeting page, built on ``meeting.html``.
 *
 * .. attribute:: meeting
 *
 *    Represented :ref:`Meeting`. The initial value is set from the JSON value of the HTML attribute
 *    of the same name.
 */
meetling.MeetingPage = document.registerElement("meetling-meeting-page",
        {extends: "body", prototype: Object.create(meetling.Page.prototype, {
    createdCallback: {value: function() {
        meetling.Page.prototype.createdCallback.call(this);
        this.meeting = JSON.parse(this.getAttribute("meeting"));
        this.querySelector(".meetling-meeting-create-agenda-item .action").addEventListener("click",
                                                                                            this);
        if (this.meeting.time) {
            this.querySelector(".meetling-meeting-meta time").textContent =
                new Date(this.meeting.time).toLocaleString("en", meetling._DATE_TIME_FORMAT);
        }
    }},

    handleEvent: {value: function(event) {
        meetling.Page.prototype.handleEvent.call(this, event);
        if (event.currentTarget ===
                this.querySelector(".meetling-meeting-create-agenda-item .action")) {
            var ul = this.querySelector(".meetling-meeting-items");
            var li = this.querySelector(".meetling-meeting-create-agenda-item");
            var editor = new meetling.AgendaItemEditor();
            editor.replaced = li;
            ul.insertBefore(editor, li);
            ul.removeChild(li);
        }
    }}
})});

/**
 * Edit meeting page, built on ``edit-meeting.html``.
 *
 * .. attribute:: meeting
 *
 *    :ref:`Meeting` to edit. ``null`` means the page is in create mode.
 */
meetling.EditMeetingPage = document.registerElement("meetling-edit-meeting-page",
        {extends: "body", prototype: Object.create(meetling.Page.prototype, {
    createdCallback: {value: function() {
        meetling.Page.prototype.createdCallback.call(this);
        this.meeting = JSON.parse(this.getAttribute("meeting"));
        this.querySelector(".meetling-edit-meeting-example-date").textContent =
            new Date().toLocaleDateString("en", meetling._DATE_FORMAT);
        this.querySelector(".meetling-edit-meeting-edit").addEventListener("submit", this);
        document.addEventListener("WebComponentsReady", this);

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
    }},

    _formatDate: {value: function() {
        return this._pikaday.getDate().toLocaleDateString("en", meetling._DATE_FORMAT);
    }},

    _onDrawPikaday: {value: function() {
        this._pikaday.el.appendChild(this._clearButton);
    }},

    handleEvent: {value: function(event) {
        meetling.Page.prototype.handleEvent.call(this, event);
        var form = this.querySelector(".meetling-edit-meeting-edit");

        if (event.target === document && event.type === "WebComponentsReady") {
            if (this.meeting && this.meeting.time) {
                var time = new Date(this.meeting.time);
                this._pikaday.setDate(time);
                var hour = time.getHours();
                var minute = time.getMinutes();
                form.elements["time"].value =
                    (hour < 10 ? "0" + hour : hour) + ":" + (minute < 10 ? "0" + minute : minute);
            }

        } else if (event.currentTarget === form && event.type === "submit") {
            event.preventDefault();

            var dateTime = null;
            var date = this._pikaday.getDate();
            var time = form.elements["time"].value;
            if (date || time || !form.elements["time"].checkValidity()) {
                if (!(date && time)) {
                    document.body.notify("Date and time are incomplete.");
                    return;
                }
                dateTime = date;
                var tokens = time.split(":");
                dateTime.setHours(parseInt(tokens[0]), parseInt(tokens[1]));
                dateTime = dateTime.toISOString();
            }

            var url = "/api/meetings";
            if (this.meeting) {
                url = "/api/meetings/" + this.meeting.id;
            }

            fetch(url, {method: "POST", credentials: "include", body: JSON.stringify({
                title: form.elements["title"].value,
                time: dateTime,
                location: form.elements["location"].value,
                description: form.elements["description"].value
            })}).then(function(response) {
                return response.json();
            }).then(function(meeting) {
                if (meeting.__type__ === "InputError") {
                    this.notify("The title is missing.");
                    return;
                }
                location.assign("/meetings/" + meeting.id);
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
        meetling.loadTemplate(this, ".meetling-agenda-item-template");
        this.classList.add("meetling-agenda-item");
        this.querySelector(".meetling-agenda-item-edit").addEventListener("click", this);
        this.item = JSON.parse(this.getAttribute("item"));
    }},

    item: {
        get: function() {
            return this._item;
        },
        set: function(value) {
            this._item = value;
            if (this._item) {
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
        meetling.loadTemplate(this, ".meetling-agenda-item-editor-template");
        this.classList.add("meetling-agenda-item-editor");
        this.querySelector("form").addEventListener("submit", this);
        this.querySelector(".action-cancel").addEventListener("click", this);
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

    handleEvent: {value: function(event) {
        var form = this.querySelector("form");
        var cancel = this.querySelector(".action-cancel");

        if (event.currentTarget === form) {
            event.preventDefault();

            if (!form.elements["duration"].checkValidity()) {
                document.body.notify("Duration is not a number.");
                return;
            }

            var url = "/api/meetings/" + document.body.meeting.id + "/items";
            if (this._item) {
                url = "/api/meetings/" + document.body.meeting.id + "/items/" + this._item.id;
            }

            fetch(url, {method: "POST", credentials: "include", body: JSON.stringify({
                title: form.elements["title"].value,
                duration: form.elements["duration"].value ?
                    parseInt(form.elements["duration"].value) : null,
                description: form.elements["description"].value
            })}).then(function(response) {
                return response.json();
            }).then(function(item) {
                if (item.__type__ === "InputError") {
                    for (var arg in item.errors) {
                        document.body.notify({
                            title: {empty: "Title is missing."},
                            duration: {not_positive: "Duration is not positive."},
                        }[arg][item.errors[arg]]);
                    }
                    return;
                }
                if (this._item) {
                    // In edit mode, update the corresponding meetling-agenda-item
                    this.replaced.item = item;
                } else {
                    // In create mode, append a new meetling-agenda-item to the list
                    var li = new meetling.AgendaItemElement();
                    li.item = item;
                    this.parentNode.insertBefore(li, this);
                }
                this._close();
            }.bind(this));

        } else if (event.currentTarget === cancel) {
            event.preventDefault();
            this._close();
        }
    }},

    _close: {value: function() {
        this.parentNode.insertBefore(this.replaced, this);
        this.parentNode.removeChild(this);
    }}
})});

/**
 * Load a template into an element *elem*.
 *
 * The template is retrieved via *selector*. If the template is not found, an :class:`Error`
 * (``template_not_found``) is thrown.
 */
meetling.loadTemplate = function(elem, selector) {
    var template = document.querySelector(selector);
    if (!template) {
        throw new Error("template_not_found");
    }

    // NOTE: Use template tags once browser support is sufficient:
    // elem.appendChild(document.importNode(template.content));
    var content = document.createDocumentFragment();
    Array.prototype.forEach.call(template.childNodes, function(child) {
        content.appendChild(child.cloneNode(true));
    });
    elem.appendChild(content);
};
