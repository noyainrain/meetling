class Meeting(Feed):
    """
    Is a :ref:`Feed`.
    """

class Application:
    """
    .. attribute:: handle_notification

       TODO.
    """

class Feed(Object):
    """
    Feed of events related to a common topic/context.

    Users can subscribe to the feed to retreive notifications about events published to it.

    ----

    .. attribute:: subscribers

       List of :class:`Users` s who subscribed to the feed.
    """

    def publish_event(self, event):
        """Publish an *event* to the feed.

        All :attr:`subscribers` (except the user who triggered the *event*) are notified about the
        *event*.
        """

    def subscribe(self):
        """
        .. http:post:: /api/(object-url)/subscribe

           Subscribe to the feed.

           If the current user is already subscribed, a TODO is returned.

           Permission: Authenticated users.
        """

    def unsubscribe(self):
        """
        .. http:post:: /api/(object-url)/unsubscribe

           Unsubscribe from the feed.

           If the current user is not subscribed, a TODO is returned.

           Permission: Authenticated users.
        """

class Event:
    """Event about an action on an *object* by an *user*.

    .. attribute:: type

       Name of the event.

    .. attribute:: object

       :class:`Object` the event happened to.

    .. attribute:: user

       :class:`User` who triggered the event.

    .. attribute:: detail

       Dictionary with additonal details about the event.
    """

    def __init__(self, type, object, user, detail={}):
        self.type = type
        self.object = object
        self.user = user
        self.detail = detail

# ------

# NOTE: where there is a subscribe, imagine also a unsubscribe...

# TODO: naming: Feed/Stream/Target/Channel/Topic
#               Event/Action/Activity

# NOTE: with the channel thinking is nice:
#       some user action event goes by default to:
#       user channel
#       object channel
#       all/global channel
#       ...
#       hm "by default" would mean that some global broker would be needed..

# Event typ: intrinsische/identifizierende eigenschaft verb+object e.g. EditCommentEvent
# user/subject is data
# what is channel? EditMeetingCommentEvent, EditSetingsCommentEvent -> type (rather not..)
#                  b) -> CommentEvent in meeting, in settings -> data (i.e. scope/context info)
#                  c) -> CommentEvent to meeting, to settings -> extra / destination / channel
# b) -> Commentable.event_feed (where should Comment publish events to)
# c) -> Commentable.event_scope (in which scope do events happen)

# NOTE Version C better than B, start with mixin, see if we need standalone, if yes implement
# OQ: Version A or C?


Event.type, .user, .object, ...

event = Event()
topic.publish_event(event) # often: object.publish_event()
app.all_topic.publish_event(event)
user.user_topic.publish_event(event)
object.object_topic.publish_event(event)
for user in comment.mentions: # comment is object
    user.mention_topic.publish_event(event) # or user.personal_topic

# shorter with utility:
mention_topics = [u.mention_topic for u in comment.mentions]
app.publish_event([topic] + mention_topics)
# all_topic, user_topic, object_topic by default

# ----

# maybe it is best not to combine the approaches - maybe notification topics are
# different from event topics? and some events are irrelevant to the pubsubapi

# connection between the approaches?
class NotifSystem:
    def foo(self):
        # all events... very crude...
        self.app.add_event_listener('*', self._handler)

    def _handler(self, event):
        # does not work, aye, channel not available
        # if would be:
        #for topic in event.topics:
        #    if isinstance(topic, SubscribableTopic):
        #        topic.publish_event(event)

class Foo:
    def somefoo(self):
        self.register_action('Foo.somefoo', user=self.app.user, object=self, topics=[...])
        # logs action to journal (or for starters sets object.modification_time and user.activty_time)
        # dispatches event
        # publishes event

# ----

meeting.dispatch_event(event)
app.all_events.dispatch_event(event)

# shorter with utility:
app.dispatch_event(meeting, event)
# all_events by default

# for plugins
app.all_events.add_event_listener('Meeting.edit', handler) # global scope -- this is really common for
                                                           # plugins, they want to do stuff on certain
                                                           # events without keeping track of all existing
                                                           # meeting objects
meeting.add_event_listener('AgendaItem.edit', handler) # specific meeting scope -- for such meetings
                                                       # need to stay in memory

meeting.add_event_listener('*', handler) # useful for real-time-push-subscribers
# below is very near to pubsub
# GET /api/meeting/(id)/feed
class MeetingFeed(ResourceHandler):
    @asynchronous
    def get(self, id):
        self.meeting = self.app.meetings[id]
        self.meeting.add_event_listener('*', self._handler)
        # client will close the connection

    def close(self):
        self.meeting.remove_event_listener('*', self._handler)

    def _handler(event):
        # some utility method
        self.write_event(event)

# VERSION A (App is broker)

class App:
    # router
    #def __init__(self):
    #    self.event_router

    def publish_event(self, topic, event):
        pass

    # NOTE: also topic could be the property of an event
    #def publish_event(self, event):
    #    pass
    #app.publish_event(Event('purr', self, self.app.user, 'cat'))

    def subscribe(self, topic):
        # POST /api/subscribe
        #self.r.sadd('feed-' + topic, self.app.user.id)

    def get_subscribers(self, topic):
        # XXX IS OKAY, but not that elegant
        # GET /api/subscribers/topic
        pass

# router
#class Catz:
#    def __init__(self):
#        self.event_router = {
#            (Cat, 'purr'): lambda e: e.object,
#            (Comment, 'edit'): lambda e: e.object.commentable.feed
#        }

# NOTE: router is one more level of indirection, really necessary?

class Cat(Commentable):
    def purr(self):
        # POST /api/cats/(id)/purr
        self.app.publish_event('cat', Event('purr', self, self.app.user))

class Comment:
    def edit(self):
        # POST /api/comments/(id)
        self.app.publish_event(self.commentable.feed, Event('edit', self, self.app.user))

# VERSION B (Feed standalone)

class Feed(Object):
    def __init__(self):
        self.subscribers

    def publish_event(self, event):
        # applicable to all versions:
        #for user in self.subscribers: OR
        #for subscription in self.subscriptions:
        #    if subscription.filter(event): OR
        #    if self.filter(subscription, event):
        #        notifications.push(Notification(user, event))

    #def filter(self, subscription, event):
    #    if 'comments' in subscription.filters:
    #        if isinstance(event.object, Comment):
    #            return True
    #    return False

    def subscribe(self, filters):
        # POST /api/feeds/(id)/subscribe
        #self.r.sadd(self.id + '.subscribers', self.app.user.id)

        # with subscriptions instead of subscribers
        #subscription = Subscription(id, user, filters)
        #self.app.r.oset(subscription.id, subscription)
        #self.app.r.sadd(self.id + '.subscriptions', subscriptions)
        #return subscription

# applicable to all versions
#class Subscription:
#    def __init__(self):
#        self.user
#        self.filters

# NOTE: filter() either in Feed or Subscription
#       if in Subscription, could be indiviudal fields comments_filter = True, etc.
#       BUT Feed.subscribe takes generic list, so would be inconsistent
#           also how would feed know which Subscription type to create? ...
#       PLUS if Feed is mixin, it is easy to override filter function, nice
#            and Subscription stays simple data object

# NOTE filter could be get rid of alltogether if all filter options would be
#      different channels:
#      Cat.feed, Cat.comment-feed, Cat.like-feed
#      PRO easier implementation, only one concept
#      CONTRA not how the user sees it: i subscribe to a object/resource/topic and
#             then i want to fine-tune
#      => both possible, write to wiki, decide later :)

class Catz:
    def create_cat(self):
        #feed = Feed()
        #cat = Cat(feed)
        #self.r.oset(feed.id, feed)
        #self.r.oset(cat.id, cat)

    def __init__(self):
                           # GET /api/global-feed
        self.global_feed = self.oget('globalfeed')

class Cat(Commentable):
    def __init__(self):
        # Because of 1:1 relation could make it available via /api/(object-url)/feed
        # instead of /api/feeds/(id)
        self.feed

    def purr(self):
        # POST /api/cats/(id)/purr
        self.feed.publish_event(Event('purr', self, self.app.user))

class Comment:
    def edit(self):
        # POST /api/comments/(id)
        self.commentable.feed.publish_event(Event('edit', self, self.app.user))

# VERSION C (Feed mixin or standalone)

class Feed(Object):
    # Either mix-in or standalone object

    def __init__(self, id):
        self.subscribers = List(...)

    def publish_event(self, event)
        pass

    def subscribe(self):
        # POST /api/(object-url)/subscribe
        #self.r.sadd(self.id + '.subscribers', self.app.user.id)

class Catz:
    def __init__(self):
                           # GET /api/global-feed
        self.global_feed = self.oget('globalfeed')

class Cat(Commentable, Feed):
    def purr(self):
        # POST /api/cats/(id)/purr
        self.publish_event(Event('purr', self, self.app.user))

class Comment:
    def edit(self):
        self.commentable.feed.publish_event(Event('edit', self, self.app.user))

class Editable:
    def __init__(self):
        # must be set by subclass, events will be published here
        self.feed

# XXX
# There could be useful subscribable class for some cases
#class Subscribable:
#    def subscribe(self):
#        # POST /api/(object-id)/subscribe
