import uuid
import logging
import datetime
from modules.helper.system import SOURCE, SOURCE_ICON, SOURCE_USER

log = logging.getLogger('helper.message')

AVAILABLE_COMMANDS = ['remove_by_user', 'remove_by_id', 'replace_by_user', 'replace_by_id']


def _validate_command(command):
    """
        Checks if command exists and raises an error 
          if it doesn't exist
    :param command: command string
    :return: command string
    """
    if command not in AVAILABLE_COMMANDS:
        raise NonExistentCommand()
    return command


def process_text_messages(func):
    def validate_class(self_class, message, **kwargs):
        if message:
            if isinstance(message, TextMessage):
                return func(self_class, message, **kwargs)
        return message
    return validate_class


def ignore_system_messages(func):
    def validate_class(self_class, message, **kwargs):
        if not isinstance(message, SystemMessage):
            return func(self_class, message, **kwargs)
        return message
    return validate_class


class NonExistentCommand(Exception):
    pass


class Message(object):
    def __init__(self):
        """
            Basic Message class
        """
        self._jsonable = []
        self._timestamp = datetime.datetime.now().isoformat()

    def json(self):
        return {attr: getattr(self, attr) for attr in self._jsonable}

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def jsonable(self):
        return self._jsonable

    @jsonable.setter
    def jsonable(self, value):
        if isinstance(value, list):
            self._jsonable = value


class CommandMessage(Message):
    def __init__(self, command=''):
        """
            Command Message class
              Used to control chat behaviour
        :param command: Which command to use
        """
        Message.__init__(self)
        self._command = _validate_command(command)
        self._jsonable += ['command']

    @property
    def command(self):
        return self._command


class RemoveMessageByUser(CommandMessage):
    def __init__(self, user, text=None):
        if text:
            CommandMessage.__init__(self, command='remove_by_user')
            self.text = text
        else:
            CommandMessage.__init__(self, command='replace_by_user')
        self._user = user if isinstance(user, list) else [user]
        self._jsonable += ['user']

    @property
    def user(self):
        return self._user


class RemoveMessageByID(CommandMessage):
    def __init__(self, message_id, text=None):
        if text:
            CommandMessage.__init__(self, command='remove_by_user')
            self.text = text
        else:
            CommandMessage.__init__(self, command='replace_by_user')
        self._message_ids = message_id if isinstance(message_id, list) else [message_id]
        self._jsonable += ['user']

    @property
    def message_ids(self):
        return self._message_ids


class TextMessage(Message):
    def __init__(self, source, source_icon, user, text,
                 emotes=None, badges=None, pm=False,
                 nick_colour=None, mid=None):
        """
            Text message used by main chat logic
        :param source: Chat source (gg/twitch/beampro etc.)
        :param source_icon: Chat icon (as url)
        :param user: nickname
        :param text: message text
        :param emotes: 
        :param pm: 
        """
        Message.__init__(self)

        self._source = source
        self._source_icon = source_icon
        self._user = user
        self._text = text
        self._emotes = [] if emotes is None else emotes
        self._badges = [] if badges is None else badges
        self._pm = pm
        self._nick_colour = nick_colour
        self._channel_name = None
        self._id = str(mid) if mid else str(uuid.uuid1())

        self._jsonable += ['user', 'text', 'emotes', 'badges',
                           'id', 'source', 'source_icon', 'pm',
                           'nick_colour', 'channel_name']

    @property
    def source(self):
        return self._source

    @property
    def source_icon(self):
        return self._source_icon

    @property
    def user(self):
        return self._user

    @property
    def text(self):
        """
        :rtype: str
        """
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    @property
    def emotes(self):
        return self._emotes

    @emotes.setter
    def emotes(self, value):
        self._emotes = value

    @property
    def badges(self):
        return self._badges

    @badges.setter
    def badges(self, value):
        self._badges = value

    @property
    def pm(self):
        return self._pm

    @pm.setter
    def pm(self, value):
        self._pm = value

    @property
    def nick_colour(self):
        return self._nick_colour

    @nick_colour.setter
    def nick_colour(self, value):
        self._nick_colour = value

    @property
    def channel_name(self):
        return self._channel_name

    @channel_name.setter
    def channel_name(self, value):
        self._channel_name = value

    @property
    def id(self):
        return self._id


class SystemMessage(TextMessage):
    def __init__(self, text, source=SOURCE, source_icon=SOURCE_ICON, user=SOURCE_USER, emotes=None, category='system'):
        """
            Text message used by main chat logic
              Serves system messages from modules
        :param source: TextMessage.source
        :param source_icon: TextMessage.source_icon
        :param user: TextMessage.user
        :param text: TextMessage.text
        :param category: System message category, can be filtered
        """
        if emotes is None:
            emotes = []
        TextMessage.__init__(self, source, source_icon, user, text, emotes)
        self._category = category

    @property
    def category(self):
        return self._category

    @property
    def user(self):
        return self._user


class Emote(object):
    def __init__(self, emote_id, emote_url):
        self._id = emote_id
        self._url = emote_url

    @property
    def id(self):
        return self._id

    @property
    def url(self):
        return self._url


class Badge(Emote):
    def __init__(self, badge_id, badge_url):
        Emote.__init__(self, badge_id, badge_url)
