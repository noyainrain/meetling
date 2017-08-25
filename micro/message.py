import string
import random
from email.message import EmailMessage
import re
from smtplib import SMTP
from urllib.parse import urlparse
from urllib.request import urlopen, Request
import json
from time import sleep

def randstr(length=16, charset=string.ascii_lowercase):
    """Generate a random string.

    The string will have the given *length* and consist of characters from *charset*.
    """
    return ''.join(random.choice(charset) for i in range(length))

class MessageError(Exception):
    pass

class Channel:
    def __init__(self, token):
        self.token = token

    @staticmethod
    def auth():
        raise NotImplementedError()

    @staticmethod
    def finish_auth(auth_request, auth):
        raise NotImplementedError()

    def send(self, msg):
        raise NotImplementedError()

class EmailChannel(Channel):
    def __init__(self, token, sender, smtp_url):
        super().__init__(token)
        self.sender = sender
        self.smtp_url = smtp_url

    @staticmethod
    def auth(email, render, sender, smtp_url):
        code = randstr()
        auth_request = '{}:{}'.format(email, code)
        EmailChannel(email, sender, smtp_url).send(render(email, code))
        return auth_request

    @staticmethod
    def finish_auth(auth_request, auth):
        email, code = tuple(auth_request.split(':'))
        if auth != code:
            raise ValueError('auth_invalid')
        return email

    def send(self, msg):
        match = re.fullmatch(r'Subject: ([^\n]+)\n\n(.+)', msg, re.DOTALL)
        if not match:
            raise ValueError('msg_invalid')

        msg = EmailMessage()
        msg['To'] = self.token
        msg['From'] = self.sender
        msg['Subject'] = match.group(1)
        msg.set_content(match.group(2))

        components = urlparse(self.smtp_url)
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
