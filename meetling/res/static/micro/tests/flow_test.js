let expect = chai.expect;

describe('Watchable', function() {
    beforeEach(function() {
        this.data = new micro.bind.Watchable();
        this.array = ['a', 'b', 'c'];
    });

    describe('set()', function() {
        it('should notify watchers', function() {
            let calls = [];
            this.data.watch('foo', (...args) => calls.push(args));
            this.data.watch('foo', {
                update(...args) {
                    calls.push(args)
                }
            });
            this.data.foo = 'bar';
            expect(calls).to.deep.equal([['foo', 'bar', undefined, undefined],
                                         ['foo', 'bar', undefined, undefined]]);
        });
    });

    describe('set() on array', function() {
        it('should notify watchers', function() {
            let calls = [];
            this.data.watch('array', {
                updateItem(...args) {
                    calls.push(args);
                }
            });
            this.data.array = this.array;
            this.data.array[2] = 'z';
            expect(this.array).to.deep.equal(['a', 'b', 'z']);
            expect(calls).to.deep.equal([['array', this.array, 2, 'z']]);
        });
    });

    describe('splice() on array', function() {
        it('should notify watchers', function() {
            let calls = [];
            this.data.watch('array', {
                update(...args) {
                    calls.push(['update'].concat(args));
                },

                insertItem(...args) {
                    calls.push(['insertItem'].concat(args));
                },

                deleteItem(...args) {
                    calls.push(['deleteItem'].concat(args));
                }
            });
            this.data.array = this.array;
            this.data.array.splice(1, 1, 'z');
            expect(this.array).to.deep.equal(['a', 'z', 'c']);
            expect(calls).to.deep.equal([
                ['update', 'array', this.array, undefined, undefined],
                ['deleteItem', 'array', this.array, 1, 'b'],
                ['insertItem', 'array', this.array, 1, 'z']
            ]);
        });
    });
});

describe('bind()', function() {
    before(function() {
        this.setupItems = function() {
            this.items = ['a', 'b', 'c'];
            document.body.innerHTML = `
                <ul data-content="list items">
                    <li data-content="item"></li>
                </ul>
            `;
            this.ul = document.querySelector('ul');
            this.data = micro.bind.bind(document.body);
            this.data.items = this.items;
            this.children = Array.from(this.ul.children);
            console.log(this.ul);
        }
    });

    describe('on update data', function() {
        it('should update DOM', function() {
            document.body.innerHTML = `
                <p data-title="title"><span data-title="title"></span></p>
            `;
            let p = document.querySelector('p');
            let span = document.querySelector('span');
            let data = micro.bind.bind(document.body);
            data.title = 'test';
            expect(p.title).to.equal('test');
            expect(span.title).to.equal('test');
        });

        it('should update DOM with content binding', function() {
            document.body.innerHTML = '<p data-content="content"></p>';
            let p = document.querySelector('p');
            let data = micro.bind.bind(document.body);
            let a = document.createElement('a');
            data.content = a;
            // TODO deep?
            expect(Array.from(p.childNodes)).to.deep.equal([a]);
        });

        it('should update DOM with visible binding', function() {
            document.body.innerHTML = '<p data-visible="visible"></p>';
            let p = document.querySelector('p');
            let data = micro.bind.bind(document.body);
            data.visible = false;
            expect(p.offsetParent).to.be.null;
        });

        it('should update DOM with transform', function() {
            let elem = document.body;
            document.body.innerHTML = '<p data-title="eq title 42"></p>';
            let p = document.querySelector('p');
            let data = micro.bind.bind(document.body);
            data.title = 'foo';
            expect(p.title).to.equal('false');
        });

        it('should update DOM with list transform', function() {
            this.setupItems();
            let foo = Array.from(this.ul.childNodes, c => c.textContent)
            expect(foo).to.deep.equal(['a', 'b', 'c']);
        });
    });

    describe('on insert item', function() {
        it('should update DOM', function() {
            this.setupItems();
            this.data.items.splice(1, 0, 'z');
            let children = Array.from(this.ul.children);
            expect(children.length).to.equal(4);
            expect(children[0]).to.equal(this.children[0]);
            expect(children[1].textContent).to.equal('z');
            expect(children[2]).to.equal(this.children[1]);
            expect(children[3]).to.equal(this.children[2]);
        });
    });

    describe('on remove item', function() {
        it('should update DOM', function() {
            this.setupItems();
            this.data.items.splice(1, 1);
            let children = Array.from(this.ul.children);
            expect(children.length).to.equal(2);
            expect(children[0]).to.equal(this.children[0]);
            expect(children[1]).to.equal(this.children[2]);
        });
    });

    describe('on update item', function() {
        it('should update DOM', function() {
            this.setupItems();
            this.data.items[1] = 'z';
            let children = Array.from(this.ul.children);
            expect(children.length).to.equal(3);
            expect(children[0]).to.equal(this.children[0]);
            expect(children[1].textContent).to.equal('z');
            expect(children[2]).to.equal(this.children[2]);
        });
    });
});

/*
* WIKI: micro client unit tests
```
.PHONY: test
test:
    node_modules/.bin/karma --single-run --browsers="$(BROWSER)"
```
  * micro: html elements (in-browser): unit test API & user actions
              if there is a bit of lib functionality here, just test it also in-browser
  * e.g. micre-menu-test: should toggle, should toggle if expanded
*/

/*describe('Menu', function() {
    beforeEach(function() {
        //this.menu = document.createElement('micro-menu');
        //document.body.textContent = '';
        //document.body.appendChild(this.menu);
    });

    it('should expand', function() {
        this.menu.querySelector('.micro-menu-toggle-secondary').click();
        expect(this.menu.classList).to.contain('micro-menu-secondary-visible');
        expect(this.menu.querySelector('.micro-menu-secondary').offsetParent).to.exist;
    });

    it('should collapse', function() {
        this.menu.classList.add('micro-menu-secondary-visible');
        this.menu.querySelector('micro-menu-toggle-secondary').click();
        expect(this.menu.classList).to.not.contain('micro-menu-secondary-visible');
        expect(this.menu.querySelector('.micro-menu-secondary').offsetParent).to.not.exist;
    });
});*/
