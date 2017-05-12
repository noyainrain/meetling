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
