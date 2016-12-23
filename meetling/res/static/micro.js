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

'use strict;'

micro = micro || {};

micro.LIST_LIMIT = 100;
micro.SHORT_DATE_TIME_FORMAT = {
    year: '2-digit',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
};

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
 * Find the first ancestor of *elem* that satisfies *predicate*.
 *
 * If no ancestor is found, ``undefined`` is returned. The function *predicate(elem)* returns
 * ``true`` if *elem* fullfills the desired criteria, ``false`` otherwise. It is called for any
 * ancestor of *elem*, from its parent up until (excluding) *top* (defaults to
 * ``document.documentElement``).
 */
micro.findAncestor = function(elem, predicate, top) {
    top = top || document.documentElement;
    for (var e = elem; e && e !== top; e = e.parentElement) {
        if (predicate(e)) {
            return e;
        }
    }
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
 *
 * .. attribute:: renderEvent
 *
 *    Subclass API: Table of event rendering hooks by event type. Used by the activity page to
 *    visualize :ref:`Event` s. A hook has the form *renderEvent(event)* and is responsible to
 *    render the given *event* to a :class:`Node`.
 */
micro.UI = document.registerElement('micro-ui',
        {extends: 'body', prototype: Object.create(HTMLBodyElement.prototype, {
    createdCallback: {value: function() {
        this.page = null;
        this._progressElem = this.querySelector('.micro-ui-progress');
        this._pageSpace = this.querySelector('main .micro-ui-inside');

        this.pages = [{url: '^/activity$', page: this._makeActivityPage}];

        this.renderEvent = {
            'editable-edit': event => {
                var a = document.createElement('a');
                a.classList.add('link');
                a.href = '/settings/edit';
                a.textContent = 'site settings';
                var userElem = document.createElement('meetling-user');
                userElem.user = event.user;
                return micro.util.formatFragment('The {settings} were edited by {user}',
                                                 {settings: a, user: userElem});
            }
        }

        this.addEventListener('click', this);
        window.addEventListener('popstate', this);

        // Register UI as global
        ui = this;

        // Cancel launch if platform checks failed
        if (!micro.launch) {
            return;
        }

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

    _makeActivityPage: {value: function(url) {
        if (!ui.staff) {
            return document.createElement('micro-forbidden-page');
        }
        return document.createElement('micro-activity-page');
    }},

    handleEvent: {value: function(event) {
        if (event.type === 'click') {
            var a = micro.findAncestor(event.target,
                function(e) { return e instanceof HTMLAnchorElement; }, this);
            // NOTE: `a.origin === location.origin` would be more elegant, but Edge does not support
            // HTMLHyperlinkElementUtils yet (see
            // https://developer.microsoft.com/en-us/microsoft-edge/platform/documentation/apireference/interfaces/htmlanchorelement/
            // ).
            if (a && a.href.startsWith(location.origin)) {
                event.preventDefault();
                this.navigate(a.pathname);
            }

        } else if (event.target === window && event.type === 'popstate') {
            this._route(location.pathname);
        }
    }}
})});

/**
 * Enhanced ordered list.
 *
 * The list is sortable by the user, i.e. an user can move an item of the list by dragging it by a
 * handle. A handle is defined by the ``micro-ol-handle`` class; if an item has no handle, it cannot
 * be moved. While an item is moving, the class ``micro-ol-li-moving` is applied to it.
 *
 * Events:
 *
 * .. describe:: moveitem
 *
 *    Dispatched if an item has been moved by the user. The *detail* object of the
 *    :class:`CustomEvent` has the following attributes: *li* is the item that has been moved, from
 *    the position directly before the reference item *from* to directly before *to*. If *from* or
 *    *to* is ``null``, it means the end of the list. Thus *from* and *to* may be used in
 *    :func:`Node.insertBefore`.
 */
micro.OL = document.registerElement('micro-ol',
        {extends: 'ol', prototype: Object.create(HTMLOListElement.prototype, {
    createdCallback: {value: function() {
        this._li = null;
        this._from = null;
        this._to = null;
        this._over = null;

        this.addEventListener('mousedown', this);
        this.addEventListener('mousemove', this);
        this.addEventListener('touchstart', this);
        this.addEventListener('touchmove', this);
    }},

    attachedCallback: {value: function() {
        window.addEventListener('mouseup', this);
        window.addEventListener('touchend', this);
    }},

    detachedCallback: {value: function() {
        window.removeEventListener('mouseup', this);
        window.removeEventListener('touchend', this);
    }},

    handleEvent: {value: function(event) {
        if (event.currentTarget === this) {
            switch (event.type) {
            case 'touchstart':
            case 'mousedown':
                // Locate li intended for moving
                var handle = micro.findAncestor(event.target,
                    function(e) { return e.classList.contains('micro-ol-handle'); }, this);
                if (!handle) {
                    break;
                }
                this._li = micro.findAncestor(handle,
                    function(e) { return e.parentElement === this; }.bind(this), this);
                if (!this._li) {
                    break;
                }

                // Prevent scrolling and text selection
                event.preventDefault();
                this._from = this._li.nextElementSibling;
                this._to = null;
                this._over = this._li;
                this._li.classList.add('micro-ol-li-moving');
                ui.classList.add('micro-ui-dragging');
                break;

            case 'touchmove':
            case 'mousemove':
                if (!this._li) {
                    break;
                }

                // Locate li the pointer is over
                var x;
                var y;
                if (event.type === 'touchmove') {
                    x = event.targetTouches[0].clientX;
                    y = event.targetTouches[0].clientY;
                } else {
                    x = event.clientX;
                    y = event.clientY;
                }
                var over = micro.findAncestor(document.elementFromPoint(x, y),
                    function(e) { return e.parentElement === this; }.bind(this), this);
                if (!over) {
                    break;
                }

                // If the moving li swaps with a larger item, the pointer is still over that item
                // after the swap. We prevent accidently swapping back on the next pointer move by
                // remembering the last item the pointer was over.
                if (over === this._over) {
                    break;
                }
                this._over = over;

                if (this._li.compareDocumentPosition(this._over) &
                        Node.DOCUMENT_POSITION_PRECEDING) {
                    this._to = this._over;
                } else {
                    this._to = this._over.nextElementSibling;
                }
                this.insertBefore(this._li, this._to);
                break;
            }

        } else if (event.currentTarget === window &&
                   ['touchend', 'mouseup'].indexOf(event.type) !== -1) {
            if (!this._li) {
                return;
            }

            this._li.classList.remove('micro-ol-li-moving');
            ui.classList.remove('micro-ui-dragging');
            if (this._to !== this._from) {
                this.dispatchEvent(new CustomEvent('moveitem',
                    {detail: {li: this._li, from: this._from, to: this._to}}));
            }
            this._li = null;
        }
    }}
})});

/**
 * Button with an associated action that runs on click.
 *
 * While an action is running, the button is suspended, i.e. it shows a progress indicator and is
 * not clickable.
 *
 * .. attribute:: run
 *
 *    Hook function of the form *run()*, which performs the associated action. If it returns a
 *    promise, the button will be suspended until the promise resolves.
 */
micro.Button = class extends HTMLButtonElement {
    createdCallback() {
        this.run = null;
        this.addEventListener('click', this);
    }

    /**
     * Trigger the button.
     *
     * The associated action is run and a promise is returned which resolves to the result of
     * :attr:`run`.
     */
    trigger() {
        if (!this.run) {
            return Promise.resolve();
        }

        let i = this.querySelector('i');
        let classes = i ? i.className : null;

        let suspend = () => {
            this.disabled = true;
            if (i) {
                i.className = 'fa fa-spinner fa-spin';
            }
        };

        let resume = () => {
            this.disabled = false;
            if (i) {
                i.className = classes;
            }
        };

        suspend();
        return Promise.resolve(this.run()).then(result => {
            resume();
            return result;
        }, e => {
            resume();
            throw e;
        });
    }

    handleEvent(event) {
        if (event.currentTarget === this && event.type === 'click') {
            if (this.form && this.type === 'submit') {
                // Prevent default form submission
                event.preventDefault();
            }
            this.trigger();
        }
    }
};

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

micro._ActivityPage = class extends HTMLElement {
    createdCallback() {
        this.appendChild(document.importNode(
            ui.querySelector('.micro-activity-page-template').content, true));
        this._showMoreButton = this.querySelector('button');
        this._showMoreButton.run = this._showMore.bind(this);
        this._start = 0;
    }

    attachedCallback() {
        this._showMoreButton.trigger();
    }

    _showMore() {
        return micro.call('GET', `/api/activity/${this._start}:`).then(events => {
            let ul = this.querySelector('.micro-timeline');
            for (let event of events) {
                let li = document.createElement('li');
                let time = document.createElement('time');
                time.dateTime = event.time;
                time.textContent =
                    new Date(event.time).toLocaleString('en', micro.SHORT_DATE_TIME_FORMAT);
                li.appendChild(time);
                li.appendChild(ui.renderEvent[event.type](event));
                ul.appendChild(li);
            }
            this.classList.toggle('micro-activity-all', events.length < micro.LIST_LIMIT);
            this._start += micro.LIST_LIMIT;
        });
    }
};

document.registerElement('micro-button', {prototype: micro.Button.prototype, extends: 'button'});
document.registerElement('micro-activity-page', micro._ActivityPage);
