from unittest import TestCase

from micro.message import EmailChannel, TelegramChannel

class EmailChannelTest(TestCase):
    def setUp(self):
        self.smtp_url = '//localhost:8025'

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
