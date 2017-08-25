from unittest import TestCase

from micro.message import EmailChannel, TelegramChannel

class EmailChannelTest(TestCase):
    def setUp(self):
        self.smtp_url = '//localhost:8025'

        hub = MessageHub(services={
            'email': {
                'smtp_url': '//localhost:8025',
                'sender': 'message@example.org',
                'render_auth_msg': lambda e, a: 'Subject: X\n\nY\n'
            },
            'telegram': {
                'api_token': '188...xrc'
            }
        })

        # AuthRequest = (uid?, code)
        #               uid only needed for (email, sms, ...) not (tg, oauth, ...)
        # Channel = (uid, token?)
        #           token not needed for (email, sms, ...) only (tg, oauth, ...)
        #           uid is just additional info for (tg, oauth, ...), not needed to communicate

        # email (stronly)
        auth_request = hub.connect('email:happy@example.org')
        write(op.id + '.auth_request', auth_request)
        # ... auth_request_id, auth via UI
        auth_request = read(op.id + '.auth_request')
        channel = hub.finish_connect(auth_request, auth)
        write(user.id + '.channel', channel)
        # ...
        channel = read(user.id + '.channel')
        hub.send(channel, 'Subject: Foo\n\nFoo\n')

        # email (Channel)
        auth_request = hub.connect('email:happy@example.org')
        write(op.id + '.auth_request', auth_request)
        # ... auth via UI
        auth_request = read(op.id + '.auth_request')
        channel = hub.finish_connect(auth_request, auth)
        write(user.id + '.channel', str(channel))
        # ...
        channel = Channel(read(user.id + '.channel'), hub) # alt: hub.make_channel(read(...))
        channel.send('Subject: Foo\n\nFoo\n')

        # email (Channel + AuthRequest)
        auth_request = hub.connect('email:happy@example.org')
        write(op.id + '.auth_request', str(auth_request))
        # ... auth via UI
        auth_request = AuthRequest(read(op.id + '.auth_request'), hub)
        channel = auth_request.finish(auth)
        write(user.id + '.channel', str(channel))
        # ...
        channel = Channel(read(user.id + '.channel'), hub)
        channel.send('Subject: Foo\n\nFoo\n')

        # ---

        # telegram (stronly)
        auth_request = hub.connect('telegram')
        channel = hub.finish_connect(auth_request, '')
        hub.send(channel, 'Foo')

        # telegram (Channel)
        auth_request = hub.connect('telegram')
        channel = hub.finish_connect(auth_request, '')
        channel.send('Foo')

        # telegram (Channel + AuthRequest)
        auth_request = hub.connect('telegram')
        channel = auth_request.finish('')
        channel.send('Foo')

    def test_auth(self):
        code = None
        def _render(email, auth):
            nonlocal code
            code = auth
            return 'Subject: Auth Important\n\nMeow!\n'

        auth_request = EmailChannel.auth('happy@example.org', _render, 'message@example.org',
                                         self.smtp_url)
        token = EmailChannel.finish_auth(auth_request, code)
        self.assertEqual(token, 'happy@example.org')

    def test_send(self):
        channel = EmailChannel('happy@example.org', 'message@example.org', self.smtp_url)
        channel.send('Subject: Notification\n\nMeow!\n')

class TelegramChannelTest(TestCase):
    def test_auth(self):
        api_token = '188662197:AAHtgXkiB6qBq2_KLYYs7pi9l3uVAvA8xrc'
        auth_request = TelegramChannel.auth(api_token)
        print('https://telegram.me/meetlingorgbot?start=' + auth_request.split('-')[1])
        token = TelegramChannel.finish_auth(auth_request, None)
        print('TOKEN', token)
        channel = TelegramChannel(token, api_token)
        channel.send('Du bist jetzt subscribed! :)')

    def test_send(self):
        api_token = '188662197:AAHtgXkiB6qBq2_KLYYs7pi9l3uVAvA8xrc'
        token = '143809254'
        channel = TelegramChannel(token, api_token)
        channel.send('Hallo duhu! :)')
