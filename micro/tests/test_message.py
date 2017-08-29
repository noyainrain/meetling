from unittest import TestCase

from micro.message import MessageHub, Channel, TelegramChannel

class EmailChannelTest(TestCase):
    def setUp(self):
        self.hub = MessageHub(services={
            'email': {
                'smtp_url': '//localhost:8025',
                'sender': 'message@example.org',
                'render_connect_msg': lambda e, a: 'Subject: X\n\nY\n'
            },
            'telegram': {
                'api_token': '188...xrc'
            }
        })

        ## AuthRequest = (uid?, code)
        ##               uid only needed for (email, sms, ...) not (tg, oauth, ...)
        ## Channel = (uid, token?)
        ##           token not needed for (email, sms, ...) only (tg, oauth, ...)
        ##           uid is just additional info for (tg, oauth, ...), not needed to communicate

        ## email (stronly)
        #auth_request = hub.connect('email:happy@example.org')
        #write(op.id + '.auth_request', auth_request)
        ## ... auth_request_id, auth via UI
        #auth_request = read(op.id + '.auth_request')
        #channel = hub.finish_connect(auth_request, auth)
        #write(user.id + '.channel', channel)
        ## ...
        #channel = read(user.id + '.channel')
        #hub.send(channel, 'Subject: Foo\n\nFoo\n')

        ## email (Channel)
        #auth_request = hub.connect('email:happy@example.org')
        #write(op.id + '.auth_request', auth_request)
        ## ... auth via UI
        #auth_request = read(op.id + '.auth_request')
        #channel = hub.finish_connect(auth_request, auth)
        #write(user.id + '.channel', str(channel))
        ## ...
        #channel = Channel(read(user.id + '.channel'), hub) # alt: hub.make_channel(read(...))
        #channel.send('Subject: Foo\n\nFoo\n')

        ## email (Channel + AuthRequest)
        #auth_request = hub.connect('email:happy@example.org')
        #write(op.id + '.auth_request', str(auth_request))
        ## ... auth via UI
        #auth_request = AuthRequest(read(op.id + '.auth_request'), hub)
        #channel = auth_request.finish(auth)
        #write(user.id + '.channel', str(channel))
        ## ...
        #channel = Channel(read(user.id + '.channel'), hub)
        #channel.send('Subject: Foo\n\nFoo\n')

        #channel = hub.connect('email', 'happy@example.org')
        #write(op.id + 'auth_request', str(channel))
        ### ... auth via UI
        #channel = Channel(read(op.id + '.auth_request'), hub)
        #channel.finish_connect(auth)
        #write(user.id + '.channel', str(channel))
        ### ...
        #channel = Channel(read(user.id + '.channel'), hub)
        #channel.send('Subject: Foo\n\nFoo\n')

        ## ---

        ## telegram (stronly)
        #auth_request = hub.connect('telegram')
        #channel = hub.finish_connect(auth_request, '')
        #hub.send(channel, 'Foo')

        ## telegram (Channel)
        #auth_request = hub.connect('telegram')
        #channel = hub.finish_connect(auth_request, '')
        #channel.send('Foo')

        ## telegram (Channel + AuthRequest)
        #auth_request = hub.connect('telegram')
        #channel = auth_request.finish('')
        #channel.send('Foo')

        #channel = hub.connect('telegram')
        #channel.finish_connect('')
        #channel.send('Foo')

    def make_hub(self, render_connect_msg=lambda c: 'Subject: X\n\nY\n'):
        return MessageHub({
            'email': {
                'smtp_url': '//localhost:8025',
                'sender': 'message@example.org',
                'render_connect_msg': render_connect_msg
            }
        })

    def test_auth(self):
        code = None
        def _render(channel):
            nonlocal code
            code = channel.secret
            return 'Subject: Connect\n\n{}\n'.format(code)
        hub = self.make_hub(_render)

        channel = hub.connect('email', 'happy@example.org')
        channel.finish_connect(code)
        self.assertTrue(channel.connected)

    def test_send(self):
        hub = self.make_hub()
        channel = hub.connect('email', 'happy@example.org', auth=False)
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
