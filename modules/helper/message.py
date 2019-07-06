import uuid
import logging
import datetime
import time
from modules.helper.system import SOURCE, SOURCE_ICON, SOURCE_USER

log = logging.getLogger('helper.message')

AVAILABLE_COMMANDS = ['remove_by_users', 'remove_by_ids', 'replace_by_users', 'replace_by_ids', 'reload']
AVAILABLE_SYSTEM_MESSAGES = ['system.chat', 'system.module']


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


def get_system_message_types():
    return AVAILABLE_SYSTEM_MESSAGES


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
    def __init__(self, only_gui=False):
        """
            Basic Message class
        """
        self._jsonable = []
        self._timestamp = datetime.datetime.now()
        self._only_gui = only_gui
        self._type = 'message'

    def json(self):
        return {'type': self._type,
                'unixtime': self.unixtime,
                'payload': {attr: getattr(self, attr) for attr in self._jsonable}}

    @property
    def type(self):
        return self._type

    @property
    def only_gui(self):
        return self._only_gui

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def unixtime(self):
        return time.mktime(self._timestamp.timetuple())

    @property
    def jsonable(self):
        return self._jsonable

    @jsonable.setter
    def jsonable(self, value):
        if isinstance(value, list):
            self._jsonable = value


class CommandMessage(Message):
    def __init__(self, command='', platform=None, **kwargs):
        """
            Command Message class
              Used to control chat behaviour
        :param command: Which command to use
        """
        Message.__init__(self, **kwargs)
        self._type = 'command'
        self._command = _validate_command(command)
        self._platform = platform
        self._jsonable += ['command', 'platform']

    @property
    def command(self):
        return self._command

    @property
    def platform(self):
        return self._platform


class RemoveMessageByUsers(CommandMessage):
    def __init__(self, users, text=None, **kwargs):
        if text:
            CommandMessage.__init__(self, command='replace_by_users', **kwargs)
            self.text = text
        else:
            CommandMessage.__init__(self, command='remove_by_users', **kwargs)
        self._users = users if isinstance(users, list) else [users]
        self._jsonable += ['users']

    @property
    def users(self):
        return self._users


class RemoveMessageByIDs(CommandMessage):
    def __init__(self, message_id, **kwargs):
        CommandMessage.__init__(self, command='remove_by_ids', **kwargs)
        self._messages = message_id if isinstance(message_id, list) else [message_id]
        self._jsonable += ['messages']

    @property
    def messages(self):
        return self._messages


class TextMessage(Message):
    def __init__(self, platform_id, icon, user, text,
                 emotes=None, badges=None, pm=False, nick_colour=None, mid=None,
                 me=False, channel_name=None, sub_message=False, **kwargs):
        """
            Text message used by main chat logic
        :param badges: Badges to display
        :param nick_colour: Nick colour
        :param mid: Message ID
        :param me: /me notation
        :param platform_id: Chat source (gg/twitch/beampro etc.)
        :param icon: Chat icon (as url)
        :param user: nickname
        :param text: message text
        :param emotes: 
        :param pm: 
        """
        Message.__init__(self, **kwargs)

        self._platform = Platform(platform_id, icon)
        self._user = user
        self._text = text
        self._emotes = [] if emotes is None else emotes
        self._badges = [] if badges is None else badges
        self._pm = pm
        self._me = me
        self._nick_colour = nick_colour
        self._channel_name = channel_name
        self._id = str(mid) if mid else str(uuid.uuid1())
        self._message_type = 'message_sub' if sub_message else 'message'

        self._jsonable += ['user', 'text', 'emotes', 'badges',
                           'id', 'platform', 'pm', 'nick_colour',
                           'channel_name', 'me', 'message_type']

    @property
    def platform(self):
        return self._platform

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value

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

    @property
    def me(self):
        return self._me

    @me.setter
    def me(self, value):
        self._me = value

    @property
    def message_type(self):
        return self._message_type

    def add_badge(self, badge_id, url):
        self._badges.append(Badge(badge_id, url))

    def add_emote(self, emote_id, url):
        self._emotes.append(Emote(emote_id, url))


class SystemMessage(TextMessage):
    def __init__(self, text, platform_id=SOURCE, icon=SOURCE_ICON, user=SOURCE_USER,
                 emotes=None, category='system', channel_name=None, **kwargs):
        """
            Text message used by main chat logic
              Serves system messages from modules
        :param platform_id: TextMessage.source
        :param icon: TextMessage.source_icon
        :param user: TextMessage.user
        :param text: TextMessage.text
        :param category: System message category, can be filtered
        """
        if emotes is None:
            emotes = []
        TextMessage.__init__(self, platform_id, icon, user, text,
                             emotes=emotes, channel_name=channel_name, **kwargs)
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


class Platform(object):
    def __init__(self, platform_id, icon):
        self._id = platform_id
        self._icon = icon

    @property
    def id(self):
        return self._id

    @property
    def icon(self):
        return self._icon
