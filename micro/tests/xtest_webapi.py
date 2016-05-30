# webapi

# Python forward compatibility
from __future__ import (division, absolute_import, print_function,
                        unicode_literals)

import json
from tornado.web import RequestHandler, ErrorHandler
from tornado.testing import AsyncTestCase, gen_test
from ..webapi import WebAPI, WebError
from ..webrestest import WebResourceTestMixin, SimpleResource

import logging
logging.basicConfig(level=logging.CRITICAL)

class WebAPITest(AsyncTestCase, WebResourceTestMixin):
    def setUp(self):
        super(WebAPITest, self).setUp()
        WebResourceTestMixin.setUp(self)

        self.webapp.add_handlers('', [
            ('/info$', self.InfoHandler),
            ('/blob$', SimpleResource, {
                'content': b'\x00',
                'content_type': 'application/octet-stream'
            }),
            ('/broken$', SimpleResource, {
                'content': 'foo',
                'content_type': 'application/json'
            }),
            ('/fixme$', ErrorHandler, {'status_code': 500})
        ])
        self.api = WebAPI(self.webapp_url)

    def tearDown(self):
        WebResourceTestMixin.tearDown(self)
        super(WebAPITest, self).tearDown()

    @gen_test
    def test_call(self):
        info = yield self.api.call('info', {'x': 'echo'})
        self.assertEqual(info.method, 'GET')
        self.assertEqual(vars(info.get_params), {'x': ['echo']})
        self.assertEqual(vars(info.post_params), {})

    @gen_test
    def test_call_post(self):
        info = yield self.api.call('info', {'x': 'echo'}, 'POST')
        self.assertEqual(info.method, 'POST')
        self.assertFalse(vars(info.get_params), {})
        self.assertEqual(vars(info.post_params), {'x': ['echo']})

    @gen_test
    def test_call_unknown_method(self):
        with self.assertRaisesRegexp(ValueError, 'method_unknown'):
            yield self.api.call('info', method='FOO')

    #@gen_test
    #def test_call_no_host(self):
    #    #TODO: socket.EAI_NODATA???
    #    api = WebAPI('http://localhoax/')
    #    with self.assertRaisesRegexp(WebError, 'service_not_found'):
    #        yield api.call('info')

    @gen_test
    def test_call_no_resource(self):
        with self.assertRaisesRegexp(WebError, 'service_not_found'):
            yield self.api.call('foo')

    @gen_test
    def test_call_no_server(self):
        self.webserver.stop()
        with self.assertRaisesRegexp(WebError, 'io_failed'):
            yield self.api.call('info')

    @gen_test
    def test_call_server_error(self):
        with self.assertRaisesRegexp(WebError, 'io_failed'):
            yield self.api.call('fixme')

    @gen_test
    def test_call_invalid_content_type(self):
        with self.assertRaisesRegexp(WebError, 'io_failed'):
            yield self.api.call('blob')

    @gen_test
    def test_call_invalid_content(self):
        with self.assertRaisesRegexp(WebError, 'io_failed'):
            yield self.api.call('broken')

    class InfoHandler(RequestHandler):
        def initialize(self):
            self._info = None

        def prepare(self):
            self.set_header('Content-Type', 'application/json')
            self._info = {
                'method': self.request.method,
                'get_params': self.request.query_arguments,
                'post_params': self.request.body_arguments
            }

        def get(self):
            self.write(json.dumps(self._info))

        def post(self):
            self.write(json.dumps(self._info))
