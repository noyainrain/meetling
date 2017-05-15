/*
 * TODO
 */

/**
 * TODO
 */

'use strict;'

micro = window.micro || {};
micro.bind = {};

micro.bind.Watchable = class {
    constructor(object) {
        object = object || {};
        let watchers = {};

        let notify = (prop, value, change, index, item) => {
            //console.log('NOTIFY', prop, change, index);
            if (prop in watchers) {
                for (let handle of watchers[prop]) {
                    handle = handle[change];
                    if (handle) {
                        handle(prop, value, index, item);
                    }
                }
            } else {
                //console.log(`no bindings for ${prop} !!`);
            }
        }

        let p = new Proxy(object, {
            get(target, prop) {
                let watch = (prop, handle) => {
                    let ws = watchers[prop];
                    if (!ws) {
                        ws = [];
                        watchers[prop] = ws;
                    }
                    ws.push(typeof handle === 'function' ? {update: handle} : handle);
                };
                //return prop === 'watch' ? watch : target[prop];
                switch(prop) {
                case 'target':
                    return target;
                case 'watch':
                    return watch;
                default:
                    return target[prop];
                }
            },

            set(target, prop, value, r) {
                if (p !== r) {
                    console.log('RECEIVER NOT PROXY');
                    /*r[prop] = value;*/
                    return true;
                }

                if (value instanceof Array) {
                    value = new Proxy(value, {
                        get(target, index) {
                            let splice = (start, deleteCount, ...items) => {
                                let res = target.splice(start, deleteCount, ...items);
                                for (let [i, item] of Object.entries(res)) {
                                    notify(prop, value, 'deleteItem', start + parseInt(i), item);
                                }
                                for (let [i, item] of Object.entries(items)) {
                                    notify(prop, value, 'insertItem', start + parseInt(i), item);
                                }
                                return res;
                            }
                            return index === 'splice' ? splice : target[index];
                        },

                        set(target, index, val) {
                            target[index] = val;
                            notify(prop, value, 'updateItem', parseInt(index), val);
                            return true;
                        }
                    });
                }

                target[prop] = value;
                notify(prop, value, 'update');
                return true;
            }
        });
        return p;
    }
}

micro.bind.bind = function(elem, data) {
    // utility: template selector, if given make documentImportNode ppend child foo...
    // or rather: bindTemplate(elem, templateSelector)
    // TODO this.elem.dataset.shadow = true

    //let subscribers = {};

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

    let stack = [];
    // XXX
    if (data) {
        stack.push(elem);
    } else {
        stack.push(...elem.children);
    }

    if (data === undefined) {
        data = new micro.bind.Watchable(Object.create(micro.bind.transforms));
    }

    let rootTag = elem.tagName.toLowerCase();


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

            let ctx = {
                data: data,
                elem: child
            }

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
                    value = values[0](ctx, ...values.slice(1));
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

micro.bind.transforms = {
    eq(ctx, a, b) {
        return a === b;
    },

    not(ctx, a) {
        return !a;
    },

    lt(ctx, a, b) {
        return a < b;
    },

    gt(ctx, a, b) {
        return a > b;
    },

    list(ctx, arr, itemName) {
        // TODO
        itemName = 'item';

        let scopes = new Map();

        let create = index => {
            let elem = ctx.elem._template.cloneNode(true);
            let scope = new micro.bind.Watchable(Object.create(ctx.data.target));
            scopes.set(elem, scope);
            micro.bind.bind(elem, scope);
            //scope[itemName] = arr[index];
            scope.item = arr[index];
            /*scope.foo = 3;
            console.log(scope.__proto__);
            console.log(ctx);
            console.log('SCOPE', scope);*/
            return elem;
        };

        let watcher = {
            insertItem(a, b, index) {
                ctx.elem.insertBefore(create(index), ctx.elem.children[index] || null);
            },

            deleteItem(a, b, index) {
                let elem = ctx.elem.children[index];
		        ctx.elem.removeChild(elem);
		        scopes.delete(elem);
            },

            updateItem(a, b, index) {
                let elem = ctx.elem.children[index];
                scopes.get(elem)[itemName] = arr[index];
            }
        }

        let key = Object.entries(ctx.data).find(([k, v]) => v === arr)[0];
        ctx.data.watch(key, watcher);

        if (!ctx.elem._template) {
            //ctx.elem._template = document.createDocumentFragment();
            /*for (let elem of ctx.elem.childNodes) {
                ctx.elem._template.appendChild(elem);
            }*/
            //ctx.elem._template.appendChild(ctx.elem.children);
            ctx.elem._template = ctx.elem.firstElementChild;
            ctx.elem.textContent = '';
        }

        /*for (i in arr) {
            watcher.insertItem(i);
        }*/

        let fragment = document.createDocumentFragment();
        for (i in arr) {
            fragment.appendChild(create(i));
        }
        return fragment;
    }
};
