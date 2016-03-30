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
 * Client toolkit for social micro web apps.
 */

"use strict;"

var micro = {};

/**
 * Thrown for HTTP JSON REST API errors.
 *
 * .. attribute:: error
 *
 *    The error object.
 *
 * .. attribute:: status
 *
 *    The associated HTTP status code.
 */
micro.APIError = function(error, status) {
    Error.call(this);
    this.error = error;
    this.status = status;
};
micro.APIError.prototype = Object.create(Error.prototype);

/**
 * Call a *method* on the HTTP JSON REST API endpoint at *url*.
 *
 * *method* is a HTTP method (e.g. ``GET`` or ``POST``). Arguments are passed as JSON object *args*.
 * A promise is returned that resolves to the result as JSON value, once the call is complete.
 *
 * If an error occurs, the promise rejects with an :class:`APIError`. For any IO related errors, it
 * rejects with a :class:`TypeError`.
 */
micro.call = function(method, url, args) {
    options = {method: method, credentials: 'include'};
    if (args) {
        options.headers = {'Content-Type': 'application/json'};
        options.body = JSON.stringify(args);
    }

    return fetch(url, options).then(function(response) {
        if (response.status > 500) {
            // Consider server errors IO errors
            throw new TypeError();
        }

        return response.json().then(function(result) {
            if (!response.ok) {
                throw new micro.APIError(result, response.status);
            }
            return result;
        }, function(e) {
            if (e instanceof SyntaxError) {
                // Consider invalid JSON an IO error
                throw new TypeError();
            } else {
                throw e;
            }
        });
    })
};

/**
 * User interface of a micro app.
 *
 * At the core of the UI are pages, where any page has a corresponding (shareable and bookmarkable)
 * URL. The UI takes care of user navigation.
 *
 * .. attribute:: page
 *
 *    The current page. May be ``null``.
 *
 * .. attribute:: pages
 *
 *    Subclass API: Table of available pages.
 *
 *    It is a list of objects with the attributes *url* and *page*, where *page* is the page to show
 *    if the requested URL matches the regular expression pattern *url*.
 *
 *    *page* is either an element name or a function. If it is an element name, the element is
 *    created and used as page. If it is a function, it has the form *page(url)* and is responsible
 *    to prepare and return a page element. *url* is the requested URL. Groups captured from the URL
 *    pattern are passed as additional arguments. The function may return a promise.
 *
 *    May be set by subclass in :meth:`init`. Defaults to ``[]``.
 */
micro.UI = document.registerElement('micro-ui',
        {extends: 'body', prototype: Object.create(HTMLBodyElement.prototype, {
    createdCallback: {value: function() {
        this.page = null;
        this.pages = [];

        this._progressElem = this.querySelector('.micro-ui-progress');
        this._pageSpace = this.querySelector('main .micro-ui-inside');

        this.addEventListener('click', this);
        window.addEventListener('popstate', this);

        // Register UI as global
        ui = this;

        // Go!
        this._progressElem.style.display = 'block';
        Promise.resolve(this.update()).then(function() {
            return this.init();
        }.bind(this)).then(function() {
            this.querySelector('.micro-ui-header').style.display = 'block';
            return this._route(location.pathname);
        }.bind(this));
    }},

    /**
     * Subclass API: Update the UI storage.
     *
     * If the storage is fresh, it will be initialized. If the storage is already up-to-date,
     * nothing will be done.
     *
     * May return a promise. Note that the UI is not available to the user before the promise
     * resolves.
     *
     * May be overridden by subclass. The default implementation does nothing. Called on startup.
     */
    update: {value: function() {}},

    /**
     * Subclass API: Initialize the UI.
     *
     * May return a promise. Note that the UI is not available to the user before the promise
     * resolves.
     *
     * May be overridden by subclass. The default implementation does nothing. Called on startup.
     */
    init: {value: function() {}},

    /**
     * Navigate to the given *url*.
     */
    navigate: {value: function(url) {
        history.pushState(null, null, url);
        this._route(url);
    }},

    _open: {value: function(page) {
        this._close();
        this._pageSpace.appendChild(page);
        this.page = page;
    }},

    _close: {value: function() {
        if (this.page) {
            this._pageSpace.removeChild(this.page);
            this.page = null;
        }
    }},

    _route: {value: function(url) {
        this._close();
        this._progressElem.style.display = 'block';

        var match = null;
        var route = null;
        for (route of this.pages) {
            match = new RegExp(route.url).exec(url);
            if (match) {
                break;
            }
        }

        return Promise.resolve().then(function() {
            if (!match) {
                return document.createElement('micro-not-found-page');
            }

            if (typeof route.page === 'string') {
                return document.createElement(route.page);
            } else {
                var args = [url].concat(match.slice(1));
                return Promise.resolve(route.page.apply(null, args)).catch(function(e) {
                    if (e instanceof micro.APIError) {
                        switch(e.error.__type__) {
                        case 'NotFoundError':
                            return document.createElement('micro-not-found-page');
                        case 'PermissionError':
                            return document.createElement('micro-forbidden-page');
                        }
                    }
                    throw e;
                });
            }
        }).then(function(page) {
            this._progressElem.style.display = 'none';
            this._open(page);
        }.bind(this));
    }},

    handleEvent: {value: function(event) {
        if (event.type === 'click') {
            // parentElement may be null if an element is detached from the DOM by a previous click
            // handler
            for (var e = event.target; e && e !== this; e = e.parentElement) {
                if (e instanceof HTMLAnchorElement) {
                    if (e.origin === location.origin) {
                        event.preventDefault();
                        this.navigate(e.pathname);
                    }
                    break;
                }
            }

        } else if (event.target === window && event.type === 'popstate') {
            this._route(location.pathname);
        }
    }}
})});

/**
 * Simple menu for (typically) actions and/or links.
 *
 * Secondary items, marked with the ``micro-menu-secondary`` class, are hidden by default and can be
 * revealed by the user with a toggle button.
 */
micro.Menu = document.registerElement("micro-menu",
        {prototype: Object.create(HTMLElement.prototype, {
    // TODO: Watch if the user modifies the content of the element and make sure the toggle button
    // is present and at the last position.

    createdCallback: {value: function() {
        this.appendChild(document.importNode(document.querySelector('.micro-menu-template').content,
                                             true));
        this.classList.add("micro-menu");
        this._toggleButton = this.querySelector(".micro-menu-toggle-secondary");
        this._toggleButton.addEventListener("click", this);
        this._update();
    }},

    _update: {value: function() {
        var secondary = this.classList.contains("micro-menu-secondary-visible");
        var i = this._toggleButton.querySelector("i");
        i.classList.remove("fa-chevron-circle-right", "fa-chevron-circle-left");
        i.classList.add(`fa-chevron-circle-${secondary ? "left" : "right"}`);
        this.querySelector(".micro-menu-toggle-secondary").title =
            `Show ${secondary ? "less" : "more"}`;
    }},

    handleEvent: {value: function(event) {
        if (event.currentTarget === this._toggleButton && event.type === "click") {
            this.classList.toggle("micro-menu-secondary-visible");
            this._update();
        }
    }}
})});

/**
 * Not found page.
 */
micro.NotFoundPage = document.registerElement('micro-not-found-page',
        {prototype: Object.create(HTMLElement.prototype, {
    createdCallback: {value: function() {
        this.appendChild(document.importNode(
            ui.querySelector('.micro-not-found-page-template').content, true));
    }}
})});

/**
 * Forbidden page.
 */
micro.ForbiddenPage = document.registerElement('micro-forbidden-page',
        {prototype: Object.create(HTMLElement.prototype, {
    createdCallback: {value: function() {
        this.appendChild(document.importNode(
            ui.querySelector('.micro-forbidden-page-template').content, true));
    }}
})});
