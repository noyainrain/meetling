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
