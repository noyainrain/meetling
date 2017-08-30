# jsonredis
# https://github.com/NoyaInRain/micro/blob/master/jsonredis.py
# part of Micro
# released into the public domain

"""Extended :class:`Redis` client for convinient use with JSON objects.

Also includes :class:`JSONRedisMapping`, an utility map interface for JSON objects.
"""

import json
from collections import Sequence, Mapping
from weakref import WeakValueDictionary
from redis.exceptions import ResponseError

class JSONRedis:
    """Extended :class:`Redis` client for convenient use with JSON objects.

    Objects are stored as JSON-encoded strings in the Redis database and en-/decoding is handled
    transparently.

    The translation from an arbitrary object to a JSON-serializable form is carried out by a given
    ``encode(object)`` function. A JSON-serializable object is one that only cosists of the types
    given in https://docs.python.org/3/library/json.html#py-to-json-table . *encode* is passed as
    *default* argument to :func:`json.dumps()`.

    The reverse translation is done by a given ``decode(json)`` function. *decode* is passed as
    *object_hook* argument to :func:`json.loads()`.

    When *caching* is enabled, objects loaded from the Redis database are cached and subsequently
    retrieved from the cache. An object stays in the cache as long as there is a reference to it and
    it is automatically removed when the Python interpreter destroys it. Thus, it is guaranteed that
    getting the same key multiple times will yield the identical object.

    .. attribute:: r

       Underlying :class:`Redis` client.

    .. attribute:: encode

       Function to encode an object to a JSON-serializable form.

    .. attribute:: decode

       Function to decode an object from a JSON-serializable form.

    .. attribute:: caching

        Switch to enable / disable object caching.
    """

    def __init__(self, r, encode=None, decode=None, caching=True):
        self.r = r
        self.encode = encode
        self.decode = decode
        self.caching = caching
        self._cache = WeakValueDictionary()

    def oget(self, key):
        """Return the object at *key*."""
        object = self._cache.get(key) if self.caching else None
        if not object:
            value = self.get(key)
            if value:
                try:
                    object = json.loads(value.decode(), object_hook=self.decode)
                except ValueError:
                    raise ResponseError()
                if self.caching:
                    self._cache[key] = object
        return object

    def oset(self, key, object):
        """Set *key* to hold *object*."""
        if self.caching:
            self._cache[key] = object
        self.set(key, json.dumps(object, default=self.encode))

    def omget(self, keys):
        """Return a list of objects for the given *keys*."""
        # NOTE: Not atomic at the moment
        return [self.oget(k) for k in keys]

    def omset(self, mapping):
        """Set each key in *mapping* to its corresponding object."""
        # NOTE: Not atomic at the moment
        for key, object in mapping.items():
            self.oset(key, object)

    def __getattr__(self, name):
        # proxy
        return getattr(self.r, name)

class JSONRedisSequence(Sequence):
    """Read-Only list interface for JSON objects stored in Redis.

    .. attribute:: r

       Underlying :class:`JSONRedis` client.

    .. attribute:: list_key

       Key of the Redis list that tracks the (keys of the) objects that the sequence contains.

    .. attribute:: pre

       Function of the form *pre()*, which is called before an object is retrieved from the
       database. May be ``None``.
    """

    def __init__(self, r, list_key, pre=None):
        self.r = r
        self.list_key = list_key
        self.pre = pre

    def __getitem__(self, key):
        if self.pre:
            self.pre()

        if isinstance(key, slice):
            if key.step:
                raise NotImplementedError()
            if key.stop == 0:
                return []
            start = 0 if key.start is None else key.start
            stop = -1 if key.stop is None else key.stop - 1
            return self.r.omget(k.decode() for k in self.r.lrange(self.list_key, start, stop))

        else:
            id = self.r.lindex(self.list_key, key)
            if not id:
                raise IndexError()
            return self.r.oget(id.decode())

    def __len__(self):
        return self.r.llen(self.list_key)

class JSONRedisMapping(Mapping):
    """Simple, read-only map interface for JSON objects stored in Redis.

    Which items the map contains is determined by the Redis list at *map_key*. Because a list is
    used, the map is ordered, i.e. items are retrieved in the order they were inserted.

    .. attribute:: r

       Underlying :class:`JSONRedis` client.

    .. attribute:: map_key

       Key of the Redis list that tracks the (keys of the) objects that the map contains.
    """

    def __init__(self, r, map_key):
        self.r = r
        self.map_key = map_key

    def __getitem__(self, key):
        # NOTE: with set:
        #if key not in self:
        if key not in iter(self):
            raise KeyError()
        return self.r.oget(key)

    def __iter__(self):
        # NOTE: with set:
        #return (k.decode() for k in self.r.smembers(self.map_key))
        return (k.decode() for k in self.r.lrange(self.map_key, 0, -1))

    def __len__(self):
        # NOTE: with set:
        #return self.r.scard(self.map_key)
        return self.r.llen(self.map_key)

     # NOTE: with set:
     #def __contains__(self, key):
     #    # optimized
     #    return self.r.sismember(self.map_key, key)

    def __repr__(self):
        return str(dict(self))
