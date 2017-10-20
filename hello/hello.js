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

/**
 * Hello UI.
 */

"use strict";

window.hello = {};

/**
 * Hello UI.
 */
hello.UI = class extends micro.UI {
    init() {
        function makeAboutPage() {
            return document.importNode(ui.querySelector(".hello-about-page-template").content, true)
                .querySelector("micro-about-page");
        }

        this.pages = this.pages.concat([
            {url: "^/$", page: "hello-start-page"},
            {url: "^/about$", page: makeAboutPage}
        ]);
    }
};

/**
 * Start page.
 */
hello.StartPage = class extends micro.Page {
    createdCallback() {
        super.createdCallback();
        this.appendChild(document.importNode(ui.querySelector(".hello-start-page-template").content,
                                             true));
        this.querySelector(".hello-start-intro a").textContent = ui.settings.title;
        this.querySelector(".hello-start-create-greeting button").run =
            this._createGreeting.bind(this);
    }

    attachedCallback() {
        micro.call("GET", "/api/greetings").then(greetings => {
            greetings.forEach(this._addGreeting, this);
        });
    }

    _addGreeting(greeting) {
        let li =
            document.importNode(ui.querySelector(".hello-greeting-template").content, true)
                .querySelector("li");
        li.querySelector("micro-user").user = greeting.authors[0];
        li.querySelector("q").textContent = greeting.text;
        let ul = this.querySelector("ul");
        ul.insertBefore(li, ul.children[1] || null);
    }

    _createGreeting() {
        let form = this.querySelector(".hello-start-create-greeting form");
        return micro.call("POST", "/api/greetings", {
            text: form.elements.text.value
        }).then(greeting => {
            form.reset();
            this._addGreeting(greeting);
        });
    }
};

document.registerElement("hello-ui", {prototype: hello.UI.prototype, extends: "body"});
document.registerElement("hello-start-page", hello.StartPage);
