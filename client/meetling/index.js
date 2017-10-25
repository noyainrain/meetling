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

/**
 * Meetling UI.
 */

"use strict";

window.meetling = {};

meetling.DATE_TIME_FORMAT = {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
    hour: "numeric",
    minute: "numeric"
};
meetling.DATE_FORMAT = {year: "numeric", month: "long", day: "numeric"};
meetling.SHORT_DATE_FORMAT = {year: "2-digit", month: "2-digit", day: "2-digit"};

meetling.makeMeetingURL = meeting => {
    let slug = micro.util.slugify(meeting.title,
                                  {max: meeting.time ? 32 - 11 : 32, reserved: ["edit"]});
    if (slug && meeting.time) {
        slug += `-${meeting.time.slice(0, 10)}`;
    }
    return `/meetings/${meeting.id.split(":")[1]}${slug}`;
};

meetling.makeMeetingLabel = meeting => {
    let label = meeting.title;
    if (meeting.time) {
        label += ` ${new Date(meeting.time).toLocaleDateString("en", meetling.SHORT_DATE_FORMAT)}`;
    }
    return label;
};

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
meetling.TimeInput = class extends HTMLInputElement {
    // NOTE: Instead of introducing a new property *timeValue*, a better approach would be to
    // override *value*. We should refactor according to the comments below, as soon as current
    // browsers expose getters and setters of :class:`Node` s.

    createdCallback() {
        this.classList.add("meetling-time-input");
        this.setAttribute("size", "5");
        this.addEventListener("change", this);
        this._value = null;
        // Better:
        // this._superValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
        this._evaluate();
    }

    // Better: value
    get timeValue() {
        return this._value;
    }

    set timeValue(value) {
        this._value = this._parseInput(value);
        this.value = this._value;
        // Better: this._superValue.set.call(this, this._value);
        this.setCustomValidity("");
    }

    handleEvent(event) {
        if (event.currentTarget === this && event.type === "change") {
            this._evaluate();
        }
    }

    _evaluate() {
        let input = this.value;
        // Better: var input = this._superValue.get.call(this);
        this._value = this._parseInput(input);
        if (this._value || !input) {
            this.setCustomValidity("");
        } else {
            this.setCustomValidity("input_bad_format");
        }
    }

    _parseInput(input) {
        let tokens = input.match(/^([0-1]?\d|2[0-3])(\D?([0-5]\d))?$/);
        if (!tokens) {
            return "";
        }

        let hour = tokens[1];
        if (hour.length === 1) {
            hour = `0${hour}`;
        }
        let minute = tokens[3] || "00";
        return `${hour}:${minute}`;
    }
};

/**
 * Compact listing of users.
 *
 * .. attribute:: users
 *
 *    List of :ref:`User` s to display. Initialized from the JSON value of the corresponding HTML
 *    attribute, if present.
 */
meetling.UserListingElement = class extends HTMLElement {
    createdCallback() {
        this._users = [];
        this.classList.add("meetling-user-listing");
    }

    get users() {
        return this._users;
    }

    set users(value) {
        this._users = value;
        this.innerHTML = "";
        for (let i = 0; i < this._users.length; i++) {
            let user = this._users[i];
            if (i > 0) {
                this.appendChild(document.createTextNode(", "));
            }
            let elem = document.createElement("micro-user");
            elem.user = user;
            this.appendChild(elem);
        }
    }
};

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
meetling.UI = class extends micro.UI {
    update() {
        let version = localStorage.version || null;

        if (!version) {
            localStorage.version = 2;
            return;
        }

        // Deprecated since 0.19.0
        if (version < 2) {
            this._storeUser(JSON.parse(localStorage.user));
            delete localStorage.user;
            localStorage.version = 2;
        }
    }

    init() {
        function makeAboutPage() {
            // NOTE: Using firstElementChild would be more elegant, but Edge does not support it yet
            // on DocumentFragment (see
            // https://wpdev.uservoice.com/forums/257854-microsoft-edge-developer/suggestions/18865648-support-the-full-set-of-apis-for-documentfragment
            // )
            return document
                .importNode(ui.querySelector(".meetling-about-page-template").content, true)
                .querySelector("micro-about-page");
        }

        this.pages = this.pages.concat([
            {url: "^/$", page: "meetling-start-page"},
            {url: "^/about$", page: makeAboutPage},
            {url: "^/create-meeting$", page: "meetling-edit-meeting-page"},
            // Compatibility routes for old meeting URLs (deprecated since 0.17.1)
            {url: "^/meetings/Meeting:([^/]+)$", page: meetling.MeetingPage.make},
            {url: "^/meetings/Meeting:([^/]+)/edit$", page: meetling.EditMeetingPage.make},
            {url: "^/meetings/([^/]+)(?:/[^/]+)?/edit$", page: meetling.EditMeetingPage.make},
            {url: "^/meetings/([^/]+)(?:/[^/]+)?$", page: meetling.MeetingPage.make}
        ]);

        Object.assign(this.renderEvent, {
            "create-meeting": event => {
                let a = document.createElement("a");
                a.classList.add("link");
                a.href = meetling.makeMeetingURL(event.detail.meeting);
                a.textContent = meetling.makeMeetingLabel(event.detail.meeting);
                let userElem = document.createElement("micro-user");
                userElem.user = event.user;
                return micro.util.formatFragment("{meeting} was created by {user}",
                                                 {meeting: a, user: userElem});
            }
        });
    }

    synthesizeMeetingTrashAgendaItemEvent(item) {
        item = Object.assign({}, item, {trashed: true});
        this.dispatchEvent(new CustomEvent("trash-agenda-item", {detail: {item}}));
    }
};

/**
 * Start page.
 */
meetling.StartPage = class extends micro.Page {
    createdCallback() {
        super.createdCallback();
        this.appendChild(document.importNode(
            ui.querySelector(".meetling-start-page-template").content, true));

        let img = this.querySelector(".micro-logo img");
        if (ui.settings.icon) {
            img.src = ui.settings.icon;
            img.style.display = "";
        } else {
            img.style.display = "none";
        }
        this.querySelector(".micro-logo span").textContent = ui.settings.title;
        this.querySelector(".meetling-start-create-example-meeting").run =
            this._createExampleMeeting.bind(this);
    }

    _createExampleMeeting() {
        return micro.call("POST", "/api/create-example-meeting").then(meeting => {
            ui.navigate(meetling.makeMeetingURL(meeting));
        });
    }
};

/**
 * Meeting page.
 */
meetling.MeetingPage = class extends micro.Page {
    static make(url, id) {
        return micro.call("GET", `/api/meetings/Meeting:${id}`).then(meeting => {
            let page = document.createElement("meetling-meeting-page");
            page.meeting = meeting;
            return page;
        });
    }

    createdCallback() {
        super.createdCallback();
        this._meeting = null;

        this.appendChild(document.importNode(
            ui.querySelector(".meetling-meeting-page-template").content, true));
        this._agendaUl = this.querySelector(".meetling-meeting-agenda > ul");
        this._itemsOL = this.querySelector(".meetling-meeting-items > ol");
        this._trashedItemsUl = this.querySelector(".meetling-meeting-trashed-items > ul");
        this._showTrashedItemsAction = this.querySelector(".meetling-meeting-show-trashed-items");
        this._hideTrashedItemsAction = this.querySelector(".meetling-meeting-hide-trashed-items");
        this._createAgendaItemAction =
            this.querySelector(".meetling-meeting-create-agenda-item .action");
        this._shareAction = this.querySelector(".meetling-meeting-share");

        this._itemsOL.addEventListener("moveitem", this);
        this._showTrashedItemsAction.addEventListener("click", this);
        this._hideTrashedItemsAction.addEventListener("click", this);
        this._createAgendaItemAction.addEventListener("click", this);
        this._shareAction.addEventListener("click", this);
    }

    attachedCallback() {
        ui.addEventListener("trash-agenda-item", this);
        ui.addEventListener("restore-agenda-item", this);

        let p1 = micro.call("GET", `/api/meetings/${this._meeting.id}/items`);
        let p2 = micro.call("GET", `/api/meetings/${this._meeting.id}/items/trashed`);
        Promise.all([p1, p2]).then(results => {
            for (let item of results[0]) {
                let li = document.createElement("li", "meetling-agenda-item");
                li.item = item;
                this._itemsOL.appendChild(li);
            }
            for (let item of results[1]) {
                let li = document.createElement("li", "meetling-agenda-item");
                li.item = item;
                this._trashedItemsUl.appendChild(li);
            }
            this._update();
        });
    }

    detachedCallback() {
        ui.removeEventListener("trash-agenda-item", this);
        ui.removeEventListener("restore-agenda-item", this);
    }

    /**
     * Represented :ref:`Meeting`.
     */
    get meeting() {
        return this._meeting;
    }

    set meeting(value) {
        this._meeting = value;
        this.caption = meetling.makeMeetingLabel(this._meeting);
        history.replaceState(null, null, meetling.makeMeetingURL(this._meeting));
        this.querySelector("h1").textContent = this._meeting.title;
        if (this._meeting.time) {
            let time = this.querySelector(".meetling-meeting-time time");
            time.dateTime = this._meeting.time;
            time.textContent = new Date(this._meeting.time).toLocaleString(
                "en", meetling.DATE_TIME_FORMAT);
        } else {
            this.querySelector(".meetling-meeting-time").style.display = "none";
        }
        if (this._meeting.location) {
            this.querySelector(".meetling-meeting-location span").textContent =
                this._meeting.location;
        } else {
            this.querySelector(".meetling-meeting-location").style.display = "none";
        }
        this.querySelector(".micro-multiline").textContent = this._meeting.description || "";
        this.querySelector(".meetling-detail meetling-user-listing").users = this._meeting.authors;
        this.querySelector(".meetling-meeting-edit").href =
            `${meetling.makeMeetingURL(this._meeting)}/edit`;
        this._update();
    }

    _update() {
        let trashedItemsCoverLi = this.querySelector(".meetling-meeting-trashed-items-cover");
        let trashedItemsLi = this.querySelector(".meetling-meeting-trashed-items");
        let trashedItemElems = trashedItemsLi.querySelectorAll(".meetling-agenda-item");
        let span = trashedItemsCoverLi.querySelector("span");
        span.textContent = span.dataset.text.split("|")[trashedItemElems.length === 1 ? 0 : 1]
            .replace("{n}", trashedItemElems.length);
        trashedItemsCoverLi.style.display = trashedItemElems.length ? "" : "none";
        trashedItemsLi.style.display = trashedItemElems.length ? "" : "none";
    }

    _getAgendaItemElement(id) {
        let elems = this.querySelectorAll(".meetling-meeting-agenda .meetling-agenda-item");
        for (let i = 0; i < elems.length; i++) {
            let li = elems[i];
            if (li.item.id === id) {
                return li;
            }
        }
        return null;
    }

    _moveAgendaItem(item, to) {
        return micro.call("POST", `/api/meetings/${this.meeting.id}/move-agenda-item`, {
            item_id: item.id,
            to_id: to ? to.id : null
        }).catch(e => {
            if (e instanceof micro.APIError && e.error.__type__ === "ValueError" &&
                    e.error.code === "item_not_found") {
                ui.synthesizeMeetingTrashAgendaItemEvent(item);
                return null;
            }
            if (e instanceof micro.APIError && e.error.__type__ === "ValueError" &&
                    e.error.code === "to_not_found") {
                // If the reference item has been trashed, retry by moving to its predecessor
                let previous = this._getAgendaItemElement(to.id).previousElementSibling;
                if (previous) {
                    previous = previous.item;
                }
                ui.synthesizeMeetingTrashAgendaItemEvent(to);
                return this._moveAgendaItem(item, previous);
            }
            throw e;
        });
    }

    handleEvent(event) {
        if (event.target === ui && event.type === "trash-agenda-item") {
            let li = this._getAgendaItemElement(event.detail.item.id);
            li.item = event.detail.item;
            this._trashedItemsUl.appendChild(li);
            this._update();

        } else if (event.target === ui && event.type === "restore-agenda-item") {
            let li = this._getAgendaItemElement(event.detail.item.id);
            li.item = event.detail.item;
            this._itemsOL.appendChild(li);
            this._update();

        } else if (event.currentTarget === this._itemsOL && event.type === "moveitem") {
            let to = event.detail.li.previousElementSibling;
            if (to) {
                to = to.item;
            }
            this._moveAgendaItem(event.detail.li.item, to);

        } else if ((event.currentTarget === this._showTrashedItemsAction ||
                    event.currentTarget === this._hideTrashedItemsAction) &&
                event.type === "click") {
            this._agendaUl.classList.toggle("meetling-meeting-agenda-trashed-items-visible");

        } else if (event.currentTarget === this._createAgendaItemAction && event.type === "click") {
            let li = this.querySelector(".meetling-meeting-create-agenda-item");
            let editor = document.createElement("li", "meetling-agenda-item-editor");
            editor.replaced = li;
            this._agendaUl.insertBefore(editor, li);
            this._agendaUl.removeChild(li);

        } else if (event.currentTarget === this._shareAction && event.type === "click") {
            let notification = document.createElement("micro-simple-notification");
            notification.content.appendChild(document.importNode(
                ui.querySelector(".meetling-share-notification-template").content, true));
            notification.content.querySelector("input").value =
                `${location.origin}${meetling.makeMeetingURL(this.meeting)}`;
            ui.notify(notification);
        }
    }
};

/**
 * Edit meeting page.
 */
meetling.EditMeetingPage = class extends micro.Page {
    static make(url, id) {
        return micro.call("GET", `/api/meetings/Meeting:${id}`).then(meeting => {
            let page = document.createElement("meetling-edit-meeting-page");
            page.meeting = meeting;
            return page;
        });
    }

    createdCallback() {
        super.createdCallback();
        this.appendChild(document.importNode(
            ui.querySelector(".meetling-edit-meeting-page-template").content, true));
        this._form = this.querySelector(".meetling-edit-meeting-edit");
        this.querySelector(".meetling-edit-meeting-example-date").textContent =
            new Date().toLocaleDateString("en", meetling.DATE_FORMAT);
        this.querySelector(".meetling-edit-meeting-edit").addEventListener("submit", this);

        this._pikaday = new Pikaday({
            field: this.querySelector(".meetling-edit-meeting-edit [name=date]"),
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
    }

    /**
     * :ref:`Meeting` to edit.
     *
     * ``null`` means the page is in create mode.
     */
    get meeting() {
        return this._meeting;
    }

    set meeting(value) {
        this._meeting = value;
        let h1 = this.querySelector("h1");
        let action = this.querySelector(".action-cancel");
        if (this._meeting) {
            this.caption = h1.textContent = `Edit ${meetling.makeMeetingLabel(this._meeting)}`;
            history.replaceState(null, null, `${meetling.makeMeetingURL(this._meeting)}/edit`);
            this._form.elements.title.value = this._meeting.title;
            if (this._meeting.time) {
                let time = new Date(this.meeting.time);
                this._pikaday.setDate(time);
                let hour = time.getHours();
                let minute = time.getMinutes();
                this._form.elements.time.timeValue =
                    `${hour < 10 ? `0${hour}` : hour}:${minute < 10 ? `0${minute}` : minute}`;
            }
            this._form.elements.location.value = this._meeting.location || "";
            this._form.elements.description.value = this._meeting.description || "";
            action.href = meetling.makeMeetingURL(this._meeting);
        } else {
            this.caption = h1.textContent = "New Meeting";
            action.href = "/";
        }
    }

    _formatDate() {
        return this._pikaday.getDate().toLocaleDateString("en", meetling.DATE_FORMAT);
    }

    _onDrawPikaday() {
        this._pikaday.el.appendChild(this._clearButton);
    }

    handleEvent(event) {
        if (event.currentTarget === this._form && event.type === "submit") {
            event.preventDefault();

            let dateTime = null;
            let date = this._pikaday.getDate();
            let time = this._form.elements.time.timeValue;
            if (date || time || !this._form.elements.time.checkValidity()) {
                if (!(date && time)) {
                    ui.notify("Date and time are incomplete.");
                    return;
                }
                dateTime = date;
                let tokens = time.split(":");
                dateTime.setHours(parseInt(tokens[0]), parseInt(tokens[1]));
                dateTime = dateTime.toISOString();
            }

            let url = "/api/meetings";
            if (this.meeting) {
                url = `/api/meetings/${this.meeting.id}`;
            }

            micro.call("POST", url, {
                title: this._form.elements.title.value,
                time: dateTime,
                location: this._form.elements.location.value,
                description: this._form.elements.description.value
            }).then(meeting => {
                ui.navigate(meetling.makeMeetingURL(meeting));
            }, e => {
                if (e instanceof micro.APIError) {
                    ui.notify("The title is missing.");
                } else {
                    throw e;
                }
            });

        } else if (event.currentTarget === this._clearButton && (event.type === "click" ||
                                                                 event.type === "touchend")) {
            this._pikaday.setDate(null);
            this._pikaday.hide();
        }
    }
};

/**
 * Agenda item element.
 *
 * .. attribute:: item
 *
 *    Represented :ref:`AgendaItem`. The initial value is set from the JSON value of the HTML
 *    attribute of the same name.
 */
meetling.AgendaItemElement = class extends HTMLLIElement {
    createdCallback() {
        this._item = null;
        this.appendChild(document.importNode(
            ui.querySelector(".meetling-agenda-item-template").content, true));
        this.classList.add("meetling-agenda-item");
        this._trashAction = this.querySelector(".meetling-agenda-item-trash");
        this._restoreAction = this.querySelector(".meetling-agenda-item-restore");
        this._trashAction.addEventListener("click", this);
        this._restoreAction.addEventListener("click", this);
        this.querySelector(".meetling-agenda-item-edit").addEventListener("click", this);
    }

    get item() {
        return this._item;
    }

    set item(value) {
        this._item = value;
        if (this._item) {
            this.classList.toggle("meetling-agenda-item-trashed", this._item.trashed);
            this.querySelector("h1").textContent = this._item.title;
            let p = this.querySelector(".meetling-agenda-item-duration");
            if (this._item.duration) {
                p.querySelector("span").textContent = `${this._item.duration}m`;
                p.style.display = "";
            } else {
                p.style.display = "none";
            }
            this.querySelector(".meetling-agenda-item-description").textContent =
                this._item.description || "";
            this.querySelector("meetling-user-listing").users = this._item.authors;
        }
    }

    handleEvent(event) {
        if (event.currentTarget === this.querySelector(".meetling-agenda-item-edit")) {
            let editor = document.createElement("li", "meetling-agenda-item-editor");
            editor.item = this._item;
            editor.replaced = this;
            this.parentNode.insertBefore(editor, this);
            this.parentNode.removeChild(this);

        } else if (event.currentTarget === this._trashAction && event.type === "click") {
            micro.call("POST", `/api/meetings/${ui.page.meeting.id}/trash-agenda-item`, {
                item_id: this._item.id
            }).catch(e => {
                // If the item has already been trashed, we continue as normal to update the UI
                if (!(e instanceof micro.APIError && e.error.__type__ === "ValueError" &&
                      e.error.code === "item_not_found")) {
                    throw e;
                }
            }).then(() => {
                ui.synthesizeMeetingTrashAgendaItemEvent(this._item);
            });

        } else if (event.currentTarget === this._restoreAction && event.type === "click") {
            micro.call("POST", `/api/meetings/${ui.page.meeting.id}/restore-agenda-item`, {
                item_id: this._item.id
            }).catch(e => {
                // If the item has already been restored, we continue as normal to update the UI
                if (!(e instanceof micro.APIError && e.error.__type__ === "ValueError" &&
                      e.error.code === "item_not_found")) {
                    throw e;
                }
            }).then(() => {
                this._item.trashed = false;
                ui.dispatchEvent(
                    new CustomEvent("restore-agenda-item", {detail: {item: this._item}}));
            });
        }
    }
};

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
meetling.AgendaItemEditor = class extends HTMLLIElement {
    createdCallback() {
        this.appendChild(document.importNode(
            ui.querySelector(".meetling-agenda-item-editor-template").content, true));
        this.classList.add("meetling-agenda-item-editor");
        this.querySelector(".action").run = this._edit.bind(this);
        this.querySelector(".action-cancel").run = this._close.bind(this);
        this.item = null;
        this.replaced = null;
    }

    get item() {
        return this._item;
    }

    set item(value) {
        this._item = value;
        if (this._item) {
            this.querySelector("h1").textContent = `Edit ${this._item.title}`;
            let form = this.querySelector("form");
            form.elements.title.value = this._item.title;
            form.elements.duration.value = this._item.duration || "";
            form.elements.description.value = this._item.description || "";
        }
    }

    _edit() {
        let form = this.querySelector("form");

        if (!form.elements.duration.checkValidity()) {
            ui.notify("Duration is not a number.");
            return null;
        }

        let url = `/api/meetings/${ui.page.meeting.id}/items`;
        if (this._item) {
            url = `/api/meetings/${ui.page.meeting.id}/items/${this._item.id}`;
        }

        return micro.call("POST", url, {
            title: form.elements.title.value,
            duration: form.elements.duration.value ? parseInt(form.elements.duration.value) : null,
            description: form.elements.description.value
        }).then(item => {
            if (this._item) {
                // In edit mode, update the corresponding meetling-agenda-item
                this.replaced.item = item;
            } else {
                // In create mode, append a new meetling-agenda-item to the list
                let li = document.createElement("li", "meetling-agenda-item");
                li.item = item;
                this.parentNode.querySelector(".meetling-meeting-items > ol").appendChild(li);
            }
            this._close();
        }, e => {
            if (e instanceof micro.APIError && e.error.__type__ === "InputError") {
                let arg = Object.keys(e.error.errors)[0];
                ui.notify({
                    title: {empty: "Title is missing."},
                    duration: {not_positive: "Duration is not positive."}
                }[arg][e.error.errors[arg]]);
            } else {
                throw e;
            }
        });
    }

    _close() {
        this.parentNode.insertBefore(this.replaced, this);
        this.parentNode.removeChild(this);
    }
};

document.registerElement("meetling-time-input",
                         {prototype: meetling.TimeInput.prototype, extends: "input"});
document.registerElement("meetling-user-listing", meetling.UserListingElement);
document.registerElement("meetling-ui", {prototype: meetling.UI.prototype, extends: "body"});
document.registerElement("meetling-start-page", meetling.StartPage);
document.registerElement("meetling-meeting-page", meetling.MeetingPage);
document.registerElement("meetling-edit-meeting-page", meetling.EditMeetingPage);
document.registerElement("meetling-agenda-item",
                         {prototype: meetling.AgendaItemElement.prototype, extends: "li"});
document.registerElement("meetling-agenda-item-editor",
                         {prototype: meetling.AgendaItemEditor.prototype, extends: "li"});
