import string
import random
from email.message import EmailMessage
import re
from smtplib import SMTP
from urllib.parse import urlparse
from urllib.request import urlopen, Request
import json
from time import sleep

# TODO: Move TelegramChannel to new design

def randstr(length=16, charset=string.ascii_lowercase):
    """Generate a random string.

    The string will have the given *length* and consist of characters from *charset*.
    """
    return ''.join(random.choice(charset) for i in range(length))

class MessageError(Exception):
    pass

class MessageHub:
    def __init__(self, services):
        self.services = services
        self.channel_types = {'email': EmailChannel, 'telegram': TelegramChannel}

    def connect(self, service, to=None, auth=True):
        return self.channel_types[service].connect(to, auth, self)

class Channel:
    def __new__(cls, str, hub):
        if isinstance(cls, Channel):
            service = str.split(':')[0]
            return hub.channel_types[service](str, hub)
        return super().__new__(cls)

    def __init__(self, str, hub):
        tokens = str.split(':')
        self.to = tokens[1] or None
        self.secret = tokens[2] or None
        self.connected = tokens[3] == 'true'
        self.hub = hub

    @staticmethod
    def connect(to, auth, hub):
        raise NotImplementedError()

    def finish_connect(self, auth):
        raise NotImplementedError()

    def send(self, msg):
        raise NotImplementedError()

    def __str__(self):
        return '{}:{}:{}:{}'.format(self.service, self.to or '', self.secret or '',
                                    'true' if self.connected else 'false')

class EmailChannel(Channel):
    service = 'email'

    @staticmethod
    def connect(to, auth, hub):
        # TODO: check to
        if auth:
            # TODO: check
            render_connect_msg = hub.services['email']['render_connect_msg']
            channel = EmailChannel('email:{}:{}:false'.format(to, randstr()), hub)
            EmailChannel('email:{}::true'.format(to), hub).send(render_connect_msg(channel))
        else:
            channel = EmailChannel('email:{}::true'.format(to), hub)
        return channel

    def finish_connect(self, auth):
        if self.connected:
            raise ValueError('channel_already_connected')
        if auth != self.secret:
            raise ValueError('auth_invalid')
        self.secret = None
        self.connected = True

    def send(self, msg):
        if not self.connected:
            raise ValueError('channel_not_connected')
        # TODO: check
        sender = self.hub.services['email']['sender']
        smtp_url = self.hub.services['email']['smtp_url']

        match = re.fullmatch(r'Subject: ([^\n]+)\n\n(.+)', msg, re.DOTALL)
        if not match:
            raise ValueError('msg_invalid')

        msg = EmailMessage()
        msg['To'] = self.to
        msg['From'] = sender
        msg['Subject'] = match.group(1)
        msg.set_content(match.group(2))

        components = urlparse(smtp_url)
        host = components.hostname or 'localhost'
        port = components.port or 25
        try:
            with SMTP(host=host, port=port) as smtp:
                smtp.send_message(msg)
        except OSError:
            raise MessageError()

class TelegramChannel(Channel):
    def __init__(self, token, api_token):
        super().__init__(token)
        self.api_token = api_token
        # TODO
        self.api_token = '188662197:AAHtgXkiB6qBq2_KLYYs7pi9l3uVAvA8xrc'

    @staticmethod
    def auth(api_token):
        return '{}-{}'.format(api_token, randstr())

    @staticmethod
    def finish_auth(auth_request, auth):
        api_token, secret = tuple(auth_request.split('-'))
        url = 'https://api.telegram.org/bot{}/getUpdates'.format(api_token)
        headers = {'Content-Type': 'application/json'}
        offset = ''

        updates = []
        while True:
            print('ping')
            x = json.dumps({
                'timeout': 60,
                'offset': offset
            }).encode('utf-8')
            updates = json.loads(urlopen(Request(url, x, headers)).read().decode('utf-8'))['result']
            for update in updates:
                print(update)
                offset = update['update_id'] + 1
                text = update['message']['text']
                s = text.split()[1]
                print('SECRET', s, secret)
                if (s == secret):
                    break
            if (s == secret):
                break

        return update['message']['chat']['id']

    def send(self, msg):
        url = 'https://api.telegram.org/bot{}/sendMessage'.format(self.api_token)
        headers = {'Content-Type': 'application/json'}
        # TODO: reply_to_message_id?
        data = json.dumps({
            'chat_id': self.token,
            'text': msg
        }).encode('utf-8')
        result = urlopen(Request(url, data, headers)).read()
        print(result)
