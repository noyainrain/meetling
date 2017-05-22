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

                if (prop === 'watch') {
                    return watch;
                }
                if (prop === 'target') {
                    return target;
                }

                let value = target[prop];
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
                return value;

                //return prop === 'watch' ? watch : target[prop];
                /*switch(prop) {
                case 'target':
                    return target;
                case 'watch':
                    return watch;
                default:
                    return target[prop];
                }*/
            },

            set(target, prop, value, r) {
                if (p !== r) {
                    console.log('RECEIVER NOT PROXY');
                    /*r[prop] = value;*/
                    return true;
                }
                target[prop] = value;
                notify(prop, value, 'update');
                return true;
            }
        });
        return p;
    }
}

micro.bind.bind = function(elem, data, {contentOnly=true, outer=null, template=null}={}) {
    console.log('OUTER', outer ? outer._micro_binding : 'nono');

    if (template) {
        elem.appendChild(document.importNode(document.querySelector(template).content, true));
    }

    elem._micro_binding = {data, outer};

    let stack = [...(function*(o) {
        while (o) {
            yield o._micro_binding.data;
            o = o._micro_binding.outer;
        }
        //return micro.bind.transforms;
    }(elem)), micro.bind.transforms];
    console.log('STACK', stack);

    let elems = contentOnly ? [...elem.children] : [elem];

    let rootTag = elem.tagName.toLowerCase();

    while (elems.length) {
        let child = elems.pop();

        let tag = `${child.tagName.toLowerCase()}`;

        for (let [elemProp, expr] of Object.entries(child.dataset)) {
            let words = expr.split(/\s+/);
            words = words.map(word => {
                return parseFloat(word) || {
                    name: word,
                    tokens: word.split('.'),
                    scope: null,
                    resolve() {
                        return this.tokens.reduce((a, v, i) => {
                            return (a === null || a === undefined) ? undefined : a[v];
                            //if (a === null || a === undefined) {
                            //    throw new TypeError(`${tokens.slice(0, i).join('.')} is ${a} in <${tag} data-${elemProp}="${expr}">`, `<${rootTag}>`);
                            //}
                        }, this.scope);
                    }
                }
            });
            //let tokens = expr.split('.');

            let ctx = {
                binding: elem,
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
            for (ref of refs) {
                ref.scope = stack.find(s => ref.tokens[0] in s );
                if (!ref.scope) {
                    throw new ReferenceError('TODO ref error');
                }
                ref.scope.watch(ref.tokens[0], update);
            }

            update();
        }

        // TODO: check if 'shadow' in child.dataset
        if (!('content' in child.dataset)) {
            elems.push(...child.children);
        }
    }

    return data;
}

micro.bind.transforms = {
    exists(ctx, a) {
        return a !== null && a !== undefined;
    },

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

    formatDate(ctx, date) {
        // TODO: remove micro dependency
        time.textContent = new Date(date).toLocaleString('en', micro.SHORT_DATE_TIME_FORMAT);
    },

    list(ctx, arr, itemName) {
        // TODO
        itemName = 'item';

        let scopes = new Map();

        let create = index => {
            let elem = ctx.elem._template.cloneNode(true);
            let scope = new micro.bind.Watchable({item: arr[index]});
            scopes.set(elem, scope);
            micro.bind.bind(elem, scope, {contentOnly: false, outer: ctx.binding});
            //scope[itemName] = arr[index];
            //scope.item = arr[index];
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
                console.log('UPDATE ITEM', a, b, index);
                let elem = ctx.elem.children[index];
                scopes.get(elem)[itemName] = arr[index];
            }
        }

        // XXX target
        let key = Object.entries(ctx.data).find(([k, v]) => v.target === arr.target)[0];
        console.log('FOUND KEY', key);
        ctx.data.watch(key, watcher);

        if (!ctx.elem._template) {
            //ctx.elem._template = document.createDocumentFragment();
            /*for (let elem of ctx.elem.childNodes) {
                ctx.elem._template.appendChild(elem);
            }*/
            //ctx.elem._template.appendChild(ctx.elem.children);
            ctx.elem._template = ctx.elem.firstElementChild;
            ctx.elem.textContent = '';
            console.log(ctx.elem);
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
