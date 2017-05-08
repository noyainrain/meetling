/*
 * TODO
 */

/**
 * TODO
 */

'use strict;'

micro = micro || {};
micro.bind = {};

micro.bind.Watchable = class {
    constructor(object) {
        object = object || {};
        let watchers = {};

        let notify = (prop, change, index) => {
            console.log('NOTIFY', prop, change, index);
            if (prop in watchers) {
                for (let handle of watchers[prop]) {
                    handle = handle[change];
                    if (handle) {
                        handle(index);
                    }
                }
            } else {
                //console.log(`no bindings for ${prop} !!`);
            }
        }

        return new Proxy(object, {
            get(target, prop) {
                let watch = (prop, handle) => {
                    let ws = watchers[prop];
                    if (!ws) {
                        ws = [];
                        watchers[prop] = ws;
                    }
                    ws.push(typeof handle === 'function' ? {update: handle} : handle);
                };
                return prop === 'watch' ? watch : target[prop];
            },

            set(target, prop, value) {
                if (value instanceof Array) {
                    value = new Proxy(value, {
                        get(target, index) {
                            let splice = (start, deleteCount, ...items) => {
                                let res = target.splice(start, deleteCount, ...items);
                                for (let [i, item] of Object.entries(res)) {
                                    notify(prop, 'deleteItem', start + parseInt(i));
                                }
                                for (let [i, item] of Object.entries(items)) {
                                    notify(prop, 'insertItem', start + parseInt(i));
                                }
                                return res;
                            }
                            return index === 'splice' ? splice : target[index];
                        },

                        set(target, index, value) {
                            target[index] = value;
                            notify(prop, 'updateItem', index);
                            return true;
                        }
                    });
                }

                target[prop] = value;
                notify(prop, 'update');
                return true;
            }
        });
    }
}

micro.bind.bind = function(elem) {
    // utility: template selector, if given make documentImportNode ppend child foo...
    // or rather: bindTemplate(elem, templateSelector)
    // TODO this.elem.dataset.shadow = true

    //let subscribers = {};

    let funcs = {
        eq(a, b) {
            return a === b;
        },

        not(a, b) {
            return a !== b;
        },

        lt(a, b) {
            return a < b;
        },

        gt(a, b) {
            return a > b;
        }
    };

    /*let data = new Proxy(Object.create(funcs), {
        set(target, prop, value) {
            target[prop] = value;
            if (!(prop in subscribers)) console.log(`no bindings for ${prop} !!`);
            for (let subscriber of subscribers[prop]) {
                subscriber();
            }
            return true;
        }
    });*/

    data = new micro.bind.Watchable(Object.create(funcs));

    let rootTag = elem.tagName.toLowerCase();

    let stack = [];
    stack.push(...elem.children);

    while(stack.length) {
        let child = stack.pop();

        let tag = `${child.tagName.toLowerCase()}`;

        for (let [elemProp, expr] of Object.entries(child.dataset)) {
            let words = expr.split(/\s+/)
            words = words.map(word => {
                return parseFloat(word) || {
                    name: word,
                    tokens: word.split('.'),

                    resolve() {
                        return this.tokens.reduce((a, v, i) => {
                            return (a === null || a === undefined) ? undefined : a[v];
                            //if (a === null || a === undefined) {
                            //    throw new TypeError(`${tokens.slice(0, i).join('.')} is ${a} in <${tag} data-${elemProp}="${expr}">`, `<${rootTag}>`);
                            //}
                        }, data);
                    }
                }
            });
            //let tokens = expr.split('.');

            let update = () => {
                let values = words.map(word => {
                    return typeof word === 'object' ? word.resolve() : word;
                });

                let value;
                if (values.length === 1) {
                    value = values[0];
                } else {
                    if (typeof values[0] !== 'function') {
                        throw new TypeError(`${words[0].name} is not a function (in <${tag} data-${elemProp}="${expr}">)`);
                    }
                    value = values[0](...values.slice(1));
                }

                console.log(`Updating <${rootTag}><${tag}>.${elemProp} to {${expr}}=${String(value).substring(0, 16).replace('\n', 'x')}${String(value).length > 16 ? '…' : ''}`);
                switch (elemProp) {
                case 'content':
                    if (value instanceof Node) {
                        child.textContent = '';
                        child.appendChild(value);
                    } else {
                        child.textContent = value;
                    }
                    break;
                case 'visible':
                    if (value) {
                        //delete child.style.display;
                        child.style.display = '';
                    } else {
                        child.style.display = 'none';
                    }
                    break;
                default:
                    child[elemProp] = value;
                }
            }

            let refs = words.filter(w => w instanceof Object);

            console.log(`Binding <${rootTag}><${tag}>.${elemProp} to ${refs.map(r => r.name).join(', ')}`);

            //for (word of words) {
            for (word of refs) {
                //if (word instanceof Object) {
                    data.watch(word.tokens[0], update);
                    /*let subs = subscribers[word.tokens[0]];
                    if (subs === undefined) {
                        subs = [];
                        subscribers[word.tokens[0]] = subs;
                    }
                    subs.push(update);*/
                //}
            }
        }

        // TODO: check if 'shadow' in child.dataset
        if (!('content' in child.dataset)) {
            stack.push(...child.children);
        }
    }

    return data;
}
