# idea about object resolvers, noch nicht ausgegoren, WIKI

class Endpoint:
    def prepare(self, *args, **kwargs):
        self.object = self.resolve(*args, **kwargs)

    def resolve_object(self, *args, **kwargs):
        raise HTTPError(404)

class _MeetingEndpoint(Endpoint):
    def resolve_object(self, id):
        return self.app.meetings[id]

class FeedSubscribeEndpoint(Endpoint):
    def post(self):
        self.object.subscribe()

class FeedUnsubscribeEndpoint(Endpoint):
    def post(self):
        self.object.unsubscribe()
