# TODO

"""TODO."""

import json
import sys
from urllib.parse import urlencode

from tornado.httpclient import AsyncHTTPClient
from tornado.gen import coroutine

class WebAPI:
    """TODO."""

    class Object(object):
        """TODO."""

        def __init__(self, attrs={}, **kwargs):
            self.__dict__.update(attrs)
            self.__dict__.update(kwargs)

        def __str__(self):
            return str(vars(self))
        __repr__ = __str__

    def __init__(self, url, default_args={}, verbose=False):
        self.url = url
        self.default_args = default_args
        self.verbose = verbose

    @coroutine
    def call(self, method, url, args={}):
        """TODO."""
        headers = {}
        url = self.url + url
        args = dict(list(self.default_args.items()) + list(args.items()))

        if method == 'GET':
            url = url + '?' + urlencode(args)
            data = None
        elif method == 'POST':
            #data = urlencode(args)
            headers = {'Content-Type': 'application/json'}
            data = json.dumps(args)
        else:
            raise ValueError('method')

        if self.verbose:
            print(method, url, file=sys.stderr)
            print('data:', data, file=sys.stderr)

        response = yield AsyncHTTPClient().fetch(url, method=method, body=data, headers=headers)
        # TODO: handle errors
        if self.verbose:
            print(response.code, file=sys.stderr)
            print('data:', response.body, file=sys.stderr)
        #response.buffer is bytesio
        #return json.load(response.buffer, object_hook=WebAPI.Object)
        return json.loads(response.body.decode(), object_hook=WebAPI.Object)
