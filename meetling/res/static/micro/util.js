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
 * Various utilities.
 */

'use strict;'

micro = micro || {};
micro.util = {};

/**
 * Format a string containing placeholders, producing a :class:`DocumentFragment`.
 *
 * *str* is a format string containing placeholders of the form ``{key}``, where *key* may consist
 * of alpha-numeric characters plus underscores and dashes. *args* is an object mapping keys to
 * values to replace. If a value is a :class:`Node` it is inserted directly into the fragment,
 * otherwise it is converted to a text node first.
 */
micro.util.formatFragment = function(str, args) {
    let fragment = document.createDocumentFragment();
    let pattern = /{([a-zA-Z0-9_-]+)}/g;
    let match = null;

    do {
        let start = pattern.lastIndex;
        match = pattern.exec(str);
        let stop = match ? match.index : str.length;
        if (stop > start) {
            fragment.appendChild(document.createTextNode(str.substring(start, stop)));
        }
        if (match) {
            let arg = args[match[1]];
            if (!(arg instanceof Node)) {
                arg = document.createTextNode(arg);
            }
            fragment.appendChild(arg);
        }
    } while (match);

    return fragment;
};

micro.util.translate = function(elem, data={}, plural={}) {
    let elems = null;
    if (elem.dataset.text || elem.dataset.textTitle) {
        elems = [elem];
    } else {
        elems = elem.querySelectorAll('[data-text], [data-text-title]');
    }
    console.log('PLURAL', plural);

    for (let i = 0; i < elems.length; i++) {
        let elem = elems[i];
        //elem.textContent = i18next.t(elem.dataset.text);
        //elem.textContent = i18next.t(elem.dataset.text, {replace: data});
        if (elem.dataset.text) {
            let options = {};
            if (elem.dataset.text in plural) {
                options.count = plural[elem.dataset.text];
            }
            elem.textContent = '';
            elem.appendChild(micro.util.formatFragment(i18next.t(elem.dataset.text, options), data));
        }
        if (elem.dataset.textTitle) {
            // TODO: options like above
            elem.title = i18next.t(elem.dataset.textTitle, data);
        }
    }

    return elem;
}
