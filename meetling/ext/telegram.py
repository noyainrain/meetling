# TODO

"""TODO"""

from micro.util import randstr
from micro.webapi import WebAPI

from tornado.gen import coroutine

#class TelegramUser:
#    def __init__(self, app, user, secret, ):
#        self.user_id = user

class Telegram:
    def __init__(self, server):
        self.server = server
        self.app = server.app
        token = '188662197:AAHtgXkiB6qBq2_KLYYs7pi9l3uVAvA8xrc' # TODO: get from some config
        self.api = WebAPI('https://api.telegram.org/bot{}/'.format(token))

    def update(self):
        print('UPDATE')
        url = 'https://tun.inrain.org' # TODO: get from some config file
        hook_path = '/telegram-update-hook/' + token
        x = yield self.telegram.api.call('POST', 'setWebhook', {'url': url + hook_path})
        print(x)

    def connect(self, user):
        secret = randstr()
        self.app.r.set(secret, user.id)
        print('https://telegram.me/meetlingorgbot?start=' + secret)

    @coroutine
    def notify(self, subscriber):
        chat_id = self.app.r.hget('telegram', subscriber.id)
        print(chat_id)
        if not chat_id:
            return
        chat_id = chat_id.decode()
        return self.api.call('POST', 'sendMessage', {'chat_id': chat_id, 'text': 'FIRST NOTIFICATION'})
