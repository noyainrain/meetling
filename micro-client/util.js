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
 * Various utilities.
 */

"use strict";

micro.util = {};

/**
 * Convert *str* to a slug, i.e. a human readable URL path segment.
 *
 * All characters are converted to lower case, non-ASCII characters are removed and all
 * non-alphanumeric symbols are replaced with a dash. The slug is limited to *max* characters and
 * prefixed with a single slash (not counting towards the limit). Note that the result is an empty
 * string if *str* does not contain any alphanumeric symbols.
 *
 * Optionally, the computed slug is checked against a list of *reserved* strings, resulting in an
 * empty string if there is a match.
 */
micro.util.slugify = (str, {max = 32, reserved = []} = {}) => {
    let slug = str.replace(/[^\x00-\x7F]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-")
        .slice(0, max).replace(/^-|-$/g, "");
    return slug && !reserved.includes(slug) ? `/${slug}` : "";
};

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
