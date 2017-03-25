# Copyright (C) 2016   CzT/Vladislav Ivanov
import irc.client
import threading
import os
import re
import random
import requests
import logging.config
import Queue
import time
from collections import OrderedDict
from modules.helper.parser import load_from_config_file
from modules.helper.module import ChatModule
from modules.helper.system import system_message, translate_key, remove_message_by_user, EMOTE_FORMAT, NA_MESSAGE
from gui import MODULE_KEY

logging.getLogger('irc').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('twitch')
headers = {'Client-ID': '5jwove9dketiiz2kozapz8rhjdsxqxc'}
emote_bits_theme = 'dark'
emote_bits_type = 'static'
emote_bits_url = 'static-cdn.jtvnw.net/bits/{theme}/{type}/{color}/{size}'
emote_smile_url = 'http://static-cdn.jtvnw.net/emoticons/v1/{id}/1.0'
NOT_FOUND = 'none'
SOURCE = 'tw'
SOURCE_ICON = 'https://www.twitch.tv/favicon.ico'
FILE_ICON = os.path.join('img', 'tw.png')
SYSTEM_USER = 'Twitch.TV'

PING_DELAY = 10

CONF_DICT = OrderedDict()
CONF_DICT['gui_information'] = {'category': 'chat'}
CONF_DICT['config'] = OrderedDict()
CONF_DICT['config']['show_pm'] = True
CONF_DICT['config']['bttv'] = True
CONF_DICT['config']['host'] = 'irc.twitch.tv'
CONF_DICT['config']['port'] = 6667
CONF_DICT['config']['show_channel_names'] = True
CONF_DICT['config']['channels_list'] = []
CONF_GUI = {
    'config': {
        'hidden': ['host', 'port'],
        'channels_list': {
            'view': 'list',
            'addable': 'true'
        }
    },
    'non_dynamic': ['config.*'],
    'icon': FILE_ICON}


class TwitchUserError(Exception):
    """Exception for twitch user error"""


class TwitchMessageHandler(threading.Thread):
    def __init__(self, queue, twitch_queue, **kwargs):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.message_queue = queue
        self.twitch_queue = twitch_queue
        self.source = SOURCE

        self.irc_class = kwargs.get('irc_class')  # type: IRC
        self.nick = kwargs.get('nick')
        self.bttv = kwargs.get('bttv_smiles_dict', {})
        self.badges = kwargs.get('badges')
        self.custom_badges = kwargs.get('custom_badges')
        self.chat_module = kwargs.get('chat_module')
        self.kwargs = kwargs

    def run(self):
        while True:
            self.process_message(self.twitch_queue.get())

    def process_message(self, msg):
        # After we receive the message we have to process the tags
        # There are multiple things that are available, but
        #  for now we use only display-name, which is case-able.
        # Also, there is slight problem with some users, they don't have
        #  the display-name tag, so we have to check their "real" username
        #  and capitalize it because twitch does so, so we do the same.
        if msg.type in ['pubmsg', 'action']:
            self._handle_message(msg)
        elif msg.type in ['clearchat']:
            self._handle_clearchat(msg)
        elif msg.type in ['usernotice']:
            self._handle_usernotice(msg)

    def _handle_badges(self, message, badges):
        for badge in badges.split(','):
            badge_tag, badge_size = badge.split('/')
            # Fix some of the names
            badge_tag = badge_tag.replace('moderator', 'mod')

            if badge_tag in self.badges:
                badge_info = self.badges.get(badge_tag)
                if 'svg' in badge_info:
                    url = badge_info.get('svg')
                elif 'image' in badge_info:
                    url = badge_info.get('image')
                else:
                    url = 'none'
            elif badge_tag in self.custom_badges:
                badge_info = self.custom_badges.get(badge_tag)['versions'][badge_size]
                url = badge_info.get('image_url_4x')
            else:
                url = NOT_FOUND
            message['badges'].append({'badge': badge_tag, 'size': badge_size, 'url': url})

    @staticmethod
    def _handle_display_name(message, name):
        message['display_name'] = name if name else message['user']

    @staticmethod
    def _handle_emotes(message, tag_value):
        for emote in tag_value.split('/'):
            emote_id, emote_pos_diap = emote.split(':')
            message['emotes'].append({'emote_id': emote_id,
                                      'positions': emote_pos_diap.split(','),
                                      'emote_url': emote_smile_url.format(id=emote_id)})

    def _handle_bttv_smiles(self, message):
        for word in message['text'].split():
            if word in self.bttv:
                bttv_smile = self.bttv.get(word)
                message['bttv_emotes'][bttv_smile['regex']] = {
                    'emote_id': bttv_smile['regex'],
                    'emote_url': 'https:{0}'.format(bttv_smile['url'])
                }

    def _handle_pm(self, message):
        if re.match('^@?{0}[ ,]?'.format(self.nick), message['text'].lower()):
            if self.chat_module.conf_params()['config']['config'].get('show_pm'):
                message['pm'] = True

    def _handle_clearchat(self, msg):
        self.message_queue.put(remove_message_by_user(msg.arguments,
                                                      text=self.kwargs['settings'].get('remove_text')))

    def _handle_usernotice(self, msg):
        for tag in msg.tags:
            tag_value, tag_key = tag.values()
            if tag_key == 'system-msg':
                msg_text = tag_value
                self.irc_class.system_message(msg_text, category='chat')
                break
        if msg.arguments:
            self._handle_message(msg, sub_message=True)

    def _handle_message(self, msg, sub_message=False):
        message = {'source': self.source,
                   'source_icon': SOURCE_ICON,
                   'badges': [],
                   'emotes': [],
                   'bttv_emotes': {},
                   'user': msg.source.split('!')[0],
                   'type': 'message',
                   'msg_type': msg.type}

        if message['user'] == 'twitchnotify':
            self.irc_class.system_message(msg.arguments.pop(), category='chat')
            return

        message['text'] = msg.arguments.pop()

        for tag in msg.tags:
            tag_value, tag_key = tag.values()
            if tag_key == 'display-name':
                self._handle_display_name(message, tag_value)
            elif tag_key == 'badges' and tag_value:
                self._handle_badges(message, tag_value)
            elif tag_key == 'emotes' and tag_value:
                self._handle_emotes(message, tag_value)

        self._handle_bttv_smiles(message)
        self._handle_pm(message)

        if sub_message:
            self._handle_sub_message(message)

        self._send_message(message)

    @staticmethod
    def _handle_sub_message(message):
        message['sub_message'] = True

    def _send_message(self, message):
        self._post_process_emotes(message)
        self._post_process_bttv_emotes(message)
        self._post_process_multiple_channels(message)
        self.message_queue.put(message)

    @staticmethod
    def _post_process_emotes(message):
        conveyor_emotes = []
        for emote in message['emotes']:
            for position in emote['positions']:
                start, end = position.split('-')
                conveyor_emotes.append({'emote_id': emote['emote_id'],
                                        'start': int(start),
                                        'end': int(end)})
        conveyor_emotes = sorted(conveyor_emotes, key=lambda k: k['start'], reverse=True)

        for emote in conveyor_emotes:
            message['text'] = u'{start}{emote}{end}'.format(start=message['text'][:emote['start']],
                                                            end=message['text'][emote['end'] + 1:],
                                                            emote=EMOTE_FORMAT.format(emote['emote_id']))

    @staticmethod
    def _post_process_bttv_emotes(message):
        for emote, data in message['bttv_emotes'].iteritems():
            message['text'] = message['text'].replace(emote, EMOTE_FORMAT.format(emote))
            message['emotes'].append(data)

    def _post_process_multiple_channels(self, message):
        channel_class = self.irc_class.main_class
        if channel_class.chat_module.conf_params()['config']['config']['show_channel_names']:
            message['channel_name'] = channel_class.display_name


class TwitchPingHandler(threading.Thread):
    def __init__(self, irc_connection, chat_module, irc_class):
        threading.Thread.__init__(self)
        self.irc_connection = irc_connection
        self.chat_module = chat_module
        self.irc_class = irc_class

    def run(self):
        log.info("Ping started")
        while self.irc_connection.connected:
            self.irc_connection.ping("keep-alive")
            try:
                self.chat_module.set_viewers(self.irc_class.nick,
                                             self.chat_module.get_viewers(self.irc_class.nick))
            except Exception as exc:
                log.exception(exc)
            time.sleep(PING_DELAY)


class IRC(irc.client.SimpleIRCClient):
    def __init__(self, queue, channel, **kwargs):
        irc.client.SimpleIRCClient.__init__(self)
        # Basic variables, twitch channel are IRC so #channel
        self.channel = "#" + channel.lower()
        self.nick = channel.lower()
        self.queue = queue
        self.twitch_queue = Queue.Queue()
        self.tw_connection = None
        self.main_class = kwargs.get('main_class')
        self.chat_module = kwargs.get('chat_module')

        self.msg_handler = TwitchMessageHandler(queue, self.twitch_queue,
                                                irc_class=self,
                                                nick=self.nick,
                                                **kwargs)
        self.msg_handler.start()

    def system_message(self, message, category='system'):
        system_message(message, self.queue,
                       source=SOURCE, icon=SOURCE_ICON, from_user=SYSTEM_USER, category=category)

    def on_disconnect(self, connection, event):
        log.info("Connection lost")
        log.debug("connection: {}".format(connection))
        log.debug("event: {}".format(event))
        self.chat_module.set_offline(self.nick)
        self.system_message(translate_key(MODULE_KEY.join(['twitch', 'connection_died'])), category='connection')
        timer = threading.Timer(5.0, self.reconnect,
                                args=[self.main_class.host, self.main_class.port, self.main_class.nickname])
        timer.start()

    def reconnect(self, host, port, nickname):
        try_count = 0
        while True:
            try_count += 1
            log.info("Reconnecting, try {0}".format(try_count))
            try:
                self.connect(host, port, nickname)
                break
            except Exception as exc:
                log.exception(exc)

    def on_welcome(self, connection, event):
        log.info("Welcome Received, joining {0} channel".format(self.channel))
        log.debug("event: {}".format(event))
        self.tw_connection = connection
        self.system_message(translate_key(MODULE_KEY.join(['twitch', 'joining'])).format(self.channel),
                            category='connection')
        self.chat_module.set_online(self.nick)
        # After we receive IRC Welcome we send request for join and
        #  request for Capabilities (Twitch color, Display Name,
        #  Subscriber, etc)
        connection.join(self.channel)
        connection.cap('REQ', ':twitch.tv/tags')
        connection.cap('REQ', ':twitch.tv/commands')
        ping_handler = TwitchPingHandler(connection, self.chat_module, self)
        ping_handler.start()

    def on_join(self, connection, event):
        log.debug("connection: {}".format(connection))
        log.debug("event: {}".format(event))
        msg = translate_key(MODULE_KEY.join(['twitch', 'join_success'])).format(self.channel)
        log.info(msg)
        self.system_message(msg, category='connection')

    def on_pubmsg(self, connection, event):
        log.debug("connection: {}".format(connection))
        log.debug("event: {}".format(event))
        self.twitch_queue.put(event)

    def on_action(self, connection, event):
        log.debug("connection: {}".format(connection))
        log.debug("event: {}".format(event))
        self.twitch_queue.put(event)

    def on_clearchat(self, connection, event):
        log.debug("connection: {}".format(connection))
        log.debug("event: {}".format(event))
        self.twitch_queue.put(event)

    def on_usernotice(self, connection, event):
        log.debug("connection: {}".format(connection))
        log.debug("event: {}".format(event))
        self.twitch_queue.put(event)


class TWThread(threading.Thread):
    def __init__(self, queue, host, port, channel, bttv_smiles, anon=True, **kwargs):
        threading.Thread.__init__(self)
        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = True
        self.queue = queue

        self.host = host
        self.port = port
        self.channel = channel
        self.bttv_smiles = bttv_smiles
        self.kwargs = kwargs
        self.chat_module = kwargs.get('chat_module')
        self.display_name = None
        self.irc = None

        if bttv_smiles:
            self.kwargs['bttv_smiles_dict'] = {}

        # For anonymous log in Twitch wants username in special format:
        #
        #        justinfan(14d)
        #    ex: justinfan54826341875412
        #
        if anon:
            nick_length = 14
            self.nickname = "justinfan"

            for number in range(0, nick_length):
                self.nickname += str(random.randint(0, 9))

    def run(self):
        try_count = 0
        # We are connecting via IRC handler.
        while True:
            try_count += 1
            log.info("Connecting, try {0}".format(try_count))
            try:
                if self.load_config():
                    self.irc = IRC(self.queue, self.channel, main_class=self, **self.kwargs)
                    self.irc.connect(self.host, self.port, self.nickname)
                    self.irc.start()
                    log.info("Connection closed")
                    break
            except TwitchUserError:
                log.critical("Unable to find twitch user, please fix")
                self.chat_module.set_offline(self.channel[1:])
                break
            except Exception as exc:
                log.exception(exc)
            time.sleep(5)

    def load_config(self):
        try:
            request = requests.get("https://api.twitch.tv/kraken/channels/{0}".format(self.channel), headers=headers)
            if request.status_code == 200:
                log.info("Channel found, continuing")
                data = request.json()
                self.display_name = data['display_name']
            elif request.status_code == 404:
                raise TwitchUserError
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except TwitchUserError:
            raise TwitchUserError
        except Exception as exc:
            log.error("Unable to get channel ID, error: {0}\nArgs: {1}".format(exc.message, exc.args))
            return False

        try:
            # Getting random IRC server to connect to
            request = requests.get("http://tmi.twitch.tv/servers?channel={0}".format(self.channel))
            if request.status_code == 200:
                self.host = random.choice(request.json()['servers']).split(':')[0]
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.error("Unable to get server list, error: {0}\nArgs: {1}".format(exc.message, exc.args))
            return False

        try:
            # Getting Better Twitch TV smiles
            if self.bttv_smiles:
                request = requests.get("https://api.betterttv.net/emotes")
                if request.status_code == 200:
                    for smile in request.json()['emotes']:
                        self.kwargs['bttv_smiles_dict'][smile.get('regex')] = smile
                else:
                    raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get BTTV smiles, error {0}\nArgs: {1}".format(exc.message, exc.args))

        try:
            # Getting standard twitch badges
            request = requests.get("https://api.twitch.tv/kraken/chat/{0}/badges".format(self.channel), headers=headers)
            if request.status_code == 200:
                self.kwargs['badges'] = request.json()
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get twitch badges, error {0}\nArgs: {1}".format(exc.message, exc.args))

        try:
            # Warning, undocumented, can change a LOT
            # Getting CUSTOM twitch badges
            request = requests.get("https://badges.twitch.tv/v1/badges/global/display")
            if request.status_code == 200:
                self.kwargs['custom_badges'] = request.json()['badge_sets']
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get twitch undocumented api badges, error {0}\n"
                        "Args: {1}".format(exc.message, exc.args))

        return True


class TwitchMessage(object):
    def __init__(self, source, text, emotes=False):
        self.type = 'pubmsg'
        self.source = '{0}!{0}@{0}.tmi.twitch.tv'.format(source)
        self.arguments = [text]
        self.tags = [
            {'key': u'badges', 'value': u'broadcaster/1'},
            {'key': u'color', 'value': u'#FFFFFF'},
            {'key': u'display-name', 'value': u'{}'.format(source)}
        ]
        if emotes:
            self.tags.append({'key': u'emotes', 'value': u'25:0-4'})


class TestTwitch(threading.Thread):
    def __init__(self, main_class):
        super(TestTwitch, self).__init__()
        self.main_class = main_class  # type: twitch
        self.main_class.rest_add('POST', 'push_message', self.send_message)
        self.tw_queue = None

    def run(self):
        while True:
            try:
                thread = self.main_class.tw_dict.items()[0][1]
                if thread.irc.twitch_queue:
                    self.tw_queue = thread.irc.twitch_queue
                    break
            except:
                continue
        log.info("twitch Testing mode online")

    def send_message(self, *args, **kwargs):
        emotes = kwargs.get('emotes', False)
        nickname = kwargs.get('nickname', 'super_tester')
        text = kwargs.get('text', 'Kappa 123')

        self.tw_queue.put(TwitchMessage(nickname, text, emotes))


class twitch(ChatModule):
    def __init__(self, queue, python_folder, **kwargs):
        ChatModule.__init__(self)
        log.info("Initializing twitch chat")

        # Reading config from main directory.
        conf_folder = os.path.join(python_folder, "conf")
        conf_file = os.path.join(conf_folder, "twitch.cfg")

        config = load_from_config_file(conf_file, CONF_DICT)
        self._conf_params.update(
            {'folder': conf_folder, 'file': conf_file,
             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
             'parser': config,
             'config': CONF_DICT,
             'gui': CONF_GUI,
             'settings': {}})

        self.queue = queue
        self.host = CONF_DICT['config']['host']
        self.port = int(CONF_DICT['config']['port'])
        self.channels_list = CONF_DICT['config']['channels_list']
        self.bttv = CONF_DICT['config']['bttv']
        self.tw_dict = {}

        if len(self.channels_list) == 1:
            if CONF_DICT['config']['show_channel_names']:
                CONF_DICT['config']['show_channel_names'] = False

        self.testing = kwargs.get('testing')
        if self.testing:
            self.testing = TestTwitch(self)

    def load_module(self, *args, **kwargs):
        ChatModule.load_module(self, *args, **kwargs)
        if 'webchat' in self._loaded_modules:
            self._loaded_modules['webchat']['class'].add_depend('twitch')
        self._conf_params['settings']['remove_text'] = self.get_remove_text()
        for channel in self.channels_list:
            self.tw_dict[channel] = TWThread(self.queue, self.host, self.port, channel, self.bttv,
                                             settings=self._conf_params['settings'], chat_module=self)
            self.tw_dict[channel].start()
        if self.testing:
            self.testing.start()

    @staticmethod
    def get_viewers(channel):
        streams_url = 'https://api.twitch.tv/kraken/streams/{0}'.format(channel)
        try:
            request = requests.get(streams_url, headers=headers)
            if request.status_code == 200:
                json_data = request.json()
                if json_data['stream']:
                    return request.json()['stream'].get('viewers', NA_MESSAGE)
                return NA_MESSAGE
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get user count, error {0}\nArgs: {1}".format(exc.message, exc.args))

    def apply_settings(self, **kwargs):
        ChatModule.apply_settings(self, **kwargs)
        if 'webchat' in kwargs.get('from_depend', []):
            self._conf_params['settings']['remove_text'] = self.get_remove_text()
