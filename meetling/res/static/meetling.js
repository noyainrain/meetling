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
        this.querySelector(".meetling-page-notification-dismiss").addEventListener("click", this);
        this.user = JSON.parse(this.getAttribute("user"));
    }},

    /**
     * Show a notification to the user.
     *
     * The notification can hold arbitrary *content* given as :class:`Node`. Alternatively,
     * *content* can be a simple message string to display.
     */
    notify: {value: function(content) {
        if (typeof content === "string") {
            var p = document.createElement("p");
            p.textContent = content;
            content = p;
        }
        var div = this.querySelector(".meetling-page-notification-content");
        div.innerHTML = "";
        div.appendChild(content);
        this.querySelector(".meetling-page-notification").style.display = "block";
    }},

    handleEvent: {value: function(event) {
        if (event.currentTarget === this.querySelector(".meetling-page-notification-dismiss")) {
            this.querySelector(".meetling-page-notification").style.display = "none";
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
        this.querySelector(".meetling-meeting-create-agenda-item .action").addEventListener("click",
                                                                                            this);
        this.meeting = JSON.parse(this.getAttribute("meeting"));
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
        this.querySelector(".meetling-edit-meeting-edit").addEventListener("submit", this);
        this.meeting = JSON.parse(this.getAttribute("meeting"));
    }},

    handleEvent: {value: function(event) {
        meetling.Page.prototype.handleEvent.call(this, event);
        var form = this.querySelector(".meetling-edit-meeting-edit");
        if (event.currentTarget === form) {
            event.preventDefault();
            var url = "/api/meetings";
            if (this.meeting) {
                url = "/api/meetings/" + this.meeting.id;
            }

            fetch(url, {method: "POST", credentials: "include", body: JSON.stringify({
                title: form.elements["title"].value,
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
                this.querySelector(".meetling-agenda-item-description").textContent =
                    this._item.description;
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
                form.elements["description"].value = this._item.description;
            }
        }
    },

    handleEvent: {value: function(event) {
        var form = this.querySelector("form");
        var cancel = this.querySelector(".action-cancel");

        if (event.currentTarget === form) {
            event.preventDefault();
            var url = "/api/meetings/" + document.body.meeting.id + "/items";
            if (this._item) {
                url = "/api/meetings/" + document.body.meeting.id + "/items/" + this._item.id;
            }

            fetch(url, {method: "POST", credentials: "include", body: JSON.stringify({
                title: form.elements["title"].value,
                description: form.elements["description"].value
            })}).then(function(response) {
                return response.json();
            }).then(function(item) {
                if (item.__type__ === "InputError") {
                    document.body.notify("The title is missing.");
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
