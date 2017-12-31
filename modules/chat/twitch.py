# Copyright (C) 2016   CzT/Vladislav Ivanov
import Queue
import logging.config
import os
import random
import re
import threading
import time

import irc.client
import requests

from modules.helper.parser import update
from modules.gui import MODULE_KEY
from modules.helper.message import TextMessage, SystemMessage, Badge, Emote, RemoveMessageByUsers
from modules.helper.module import ChatModule
from modules.helper.system import translate_key, EMOTE_FORMAT, NA_MESSAGE, register_iodc
from modules.interface.types import LCStaticBox, LCPanel, LCText, LCBool, LCButton

logging.getLogger('irc').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('twitch')
headers = {'Client-ID': '5jwove9dketiiz2kozapz8rhjdsxqxc'}
BITS_THEME = 'dark'
BITS_TYPE = 'animated'
BITS_URL = 'http://static-cdn.jtvnw.net/bits/{theme}/{type}/{color}/{size}'
EMOTE_SMILE_URL = 'http://static-cdn.jtvnw.net/emoticons/v1/{id}/1.0'
NOT_FOUND = 'none'
SOURCE = 'tw'
SOURCE_ICON = 'https://www.twitch.tv/favicon.ico'
FILE_ICON = os.path.join('img', 'tw.png')
SYSTEM_USER = 'Twitch.TV'
BITS_REGEXP = r'(^|\s)(\w+{})(?=(\s|$))'
API_URL = 'https://api.twitch.tv/kraken/{}'

PING_DELAY = 10

CONF_DICT = LCPanel(icon=FILE_ICON)
CONF_DICT['config'] = LCStaticBox()
CONF_DICT['config']['host'] = LCText('irc.twitch.tv')
CONF_DICT['config']['port'] = LCText(6667)
CONF_DICT['config']['show_pm'] = LCBool(True)
CONF_DICT['config']['bttv'] = LCBool(True)
CONF_DICT['config']['show_channel_names'] = LCBool(True)
CONF_DICT['config']['show_nickname_colors'] = LCBool(False)
CONF_DICT['config']['register_oidc'] = LCButton(register_iodc)

CONF_GUI = {
    'config': {
        'hidden': ['host', 'port'],
        'channels_list': {
            'view': 'list',
            'addable': 'true'
        }
    },
    'non_dynamic': ['config.host', 'config.port', 'config.bttv'],
    'ignored_sections': ['config.register_oidc'],
}


class TwitchUserError(Exception):
    """Exception for twitch user error"""


class TwitchNormalDisconnect(Exception):
    """Normal Disconnect exception"""


class TwitchAPIError(Exception):
    """Exception of API"""


class TwitchTextMessage(TextMessage):
    def __init__(self, user, text, me):
        self.bttv_emotes = {}
        TextMessage.__init__(self, platform_id=SOURCE, icon=SOURCE_ICON,
                             user=user, text=text, me=me)


class TwitchSystemMessage(SystemMessage):
    def __init__(self, text, category='system', **kwargs):
        SystemMessage.__init__(self, text, platform_id=SOURCE, icon=SOURCE_ICON,
                               user=SYSTEM_USER, category=category, **kwargs)


class TwitchEmote(Emote):
    def __init__(self, emote_id, emote_url, positions):
        Emote.__init__(self, emote_id=emote_id, emote_url=emote_url)
        self.positions = positions


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
        if msg.type in ['pubmsg']:
            self._handle_message(msg)
        elif msg.type in ['action']:
            self._handle_message(msg, me=True)
        elif msg.type in ['clearchat']:
            self._handle_clearchat(msg)
        elif msg.type in ['usernotice']:
            self._handle_usernotice(msg)

    def _handle_badges(self, message, badges):
        for badge in badges.split(','):
            badge_tag, badge_size = badge.split('/')
            # Fix some of the names
            badge_tag = badge_tag.replace('moderator', 'mod')

            if badge_tag in self.custom_badges:
                badge_info = self.custom_badges.get(badge_tag)['versions'][badge_size]
                url = badge_info.get('image_url_4x',
                                     badge_info.get('image_url_2x',
                                                    badge_info.get('image_url_1x')))
            elif badge_tag in self.badges:
                badge_info = self.badges.get(badge_tag)
                if 'svg' in badge_info:
                    url = badge_info.get('svg')
                elif 'image' in badge_info:
                    url = badge_info.get('image')
                else:
                    url = 'none'
            else:
                url = NOT_FOUND
            message.badges.append(Badge(badge_tag, url))

    @staticmethod
    def _handle_display_name(message, name):
        message.user = name if name else message.user

    @staticmethod
    def _handle_emotes(message, tag_value):
        for emote in tag_value.split('/'):
            emote_id, emote_pos_diap = emote.split(':')
            message.emotes.append(
                TwitchEmote(emote_id,
                            EMOTE_SMILE_URL.format(id=emote_id),
                            emote_pos_diap.split(','))
            )

    def _handle_bttv_smiles(self, message):
        for word in message.text.split():
            if word in self.bttv:
                bttv_smile = self.bttv.get(word)
                message.bttv_emotes[bttv_smile['regex']] = Emote(
                    bttv_smile['regex'],
                    'https:{0}'.format(bttv_smile['url'])
                )

    def _handle_pm(self, message):
        if re.match('^@?{0}[ ,]?'.format(self.nick), message.text.lower()):
            if self.chat_module.conf_params()['config']['config'].get('show_pm'):
                message.pm = True

    def _handle_clearchat(self, msg, text=None):
        if self.chat_module.conf_params()['config']['config']['show_channel_names']:
            text = self.kwargs['settings'].get('remove_text')
        self.message_queue.put(
            RemoveMessageByUsers(msg.arguments,
                                 text=text,
                                 platform=SOURCE))

    def _handle_usernotice(self, msg):
        for tag in msg.tags:
            tag_value, tag_key = tag.values()
            if tag_key == 'system-msg':
                msg_text = tag_value
                self.irc_class.system_message(msg_text, category='chat')
                break
        if msg.arguments:
            self._handle_message(msg, sub_message=True)

    def _handle_message(self, msg, sub_message=False, me=False):
        message = TwitchTextMessage(msg.source.split('!')[0], msg.arguments.pop(), me)
        if message.user == 'twitchnotify':
            self.irc_class.queue.put(TwitchSystemMessage(message.text, category='chat'))

        for tag in msg.tags:
            tag_value, tag_key = tag.values()
            if tag_key == 'display-name':
                self._handle_display_name(message, tag_value)
            elif tag_key == 'badges' and tag_value:
                self._handle_badges(message, tag_value)
            elif tag_key == 'emotes' and tag_value:
                self._handle_emotes(message, tag_value)
            elif tag_key == 'bits' and tag_value:
                self._handle_bits(message, tag_value)
            elif tag_key == 'color' and tag_value:
                self._handle_viewer_color(message, tag_value)

        self._handle_bttv_smiles(message)
        self._handle_pm(message)

        if sub_message:
            self._handle_sub_message(message)

        self._send_message(message)

    def _handle_viewer_color(self, message, value):
        if self.irc_class.chat_module.conf_params()['config']['config']['show_nickname_colors']:
            message.nick_colour = value

    @staticmethod
    def _handle_bits(message, amount):
        regexp = re.search(BITS_REGEXP.format(amount), message.text)
        emote = regexp.group(2)
        emote_smile = '{}{}'.format(emote, amount)

        if amount >= 10000:
            color = 'red'
        elif amount >= 5000:
            color = 'blue'
        elif amount >= 1000:
            color = 'green'
        elif amount >= 100:
            color = 'purple'
        else:
            color = 'gray'

        message.bits = {
            'bits': emote_smile,
            'amount': amount,
            'theme': BITS_THEME,
            'type': BITS_TYPE,
            'color': color,
            'size': 4
        }
        message.text = message.text.replace(emote_smile, EMOTE_FORMAT.format(emote_smile))

    @staticmethod
    def _handle_sub_message(message):
        message.sub_message = True
        message.jsonable += ['sub_message']

    def _send_message(self, message):
        self._post_process_emotes(message)
        self._post_process_bttv_emotes(message)
        self._post_process_multiple_channels(message)
        self._post_process_bits(message)
        self.message_queue.put(message)

    @staticmethod
    def _post_process_bits(message):
        if not hasattr(message, 'bits'):
            return
        bits = message.bits
        message.emotes.append(Emote(
            bits['bits'],
            BITS_URL.format(
                theme=bits['theme'],
                type=bits['type'],
                color=bits['color'],
                size=bits['size']
            )
        ))

    @staticmethod
    def _post_process_emotes(message):
        conveyor_emotes = []
        for emote in message.emotes:
            for position in emote.positions:
                start, end = position.split('-')
                conveyor_emotes.append({'emote_id': emote.id,
                                        'start': int(start),
                                        'end': int(end)})
        conveyor_emotes = sorted(conveyor_emotes, key=lambda k: k['start'], reverse=True)

        for emote in conveyor_emotes:
            message.text = u'{start}{emote}{end}'.format(start=message.text[:emote['start']],
                                                         end=message.text[emote['end'] + 1:],
                                                         emote=EMOTE_FORMAT.format(emote['emote_id']))

    @staticmethod
    def _post_process_bttv_emotes(message):
        for emote, data in message.bttv_emotes.iteritems():
            message.text = message.text.replace(emote, EMOTE_FORMAT.format(emote))
            message.emotes.append(data)

    def _post_process_multiple_channels(self, message):
        channel_class = self.irc_class.main_class
        if channel_class.chat_module.conf_params()['config']['config']['show_channel_names']:
            message.channel_name = channel_class.display_name


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
        self.queue.put(TwitchSystemMessage(message, category=category, channel_name=self.nick))

    def on_disconnect(self, connection, event):
        if 'CLOSE_OK' in event.arguments:
            log.info("Connection closed")
            self.system_message(
                translate_key(MODULE_KEY.join(['twitch', 'connection_closed'])).format(self.nick),
                category='connection')
            raise TwitchNormalDisconnect()
        else:
            log.info("Connection lost")
            log.debug("connection: {}".format(connection))
            log.debug("event: {}".format(event))
            self.chat_module.set_channel_offline(self.nick)
            self.system_message(
                translate_key(MODULE_KEY.join(['twitch', 'connection_died'])).format(self.nick),
                category='connection')
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
        self.chat_module.set_channel_online(self.nick)
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
        self.channel_id = None
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
                    self.chat_module.set_channel_online(self.nickname)
                    self.irc.start()
                    log.info("Connection closed")
                    break
            except TwitchUserError:
                log.critical("Unable to find twitch user, please fix")
                self.chat_module.set_offline(self.nickname)
                break
            except TwitchNormalDisconnect:
                log.info("Twitch closing")
                self.chat_module.set_offline(self.nickname)
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
                self.channel_id = data['_id']
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

        try:
            # Warning, undocumented, can change a LOT
            # Getting CUSTOM twitch badges
            badges_url = "https://badges.twitch.tv/v1/badges/channels/{0}/display"
            request = requests.get(badges_url.format(self.channel_id))
            if request.status_code == 200:
                update(self.kwargs['custom_badges'], request.json()['badge_sets'])
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get twitch undocumented api badges, error {0}\n"
                        "Args: {1}".format(exc.message, exc.args))

        return True

    def stop(self):
        self.irc.tw_connection.disconnect("CLOSE_OK")


class TwitchMessage(object):
    def __init__(self, source, text, emotes=False, bits=False):
        self.type = 'pubmsg'
        self.source = '{0}!{0}@{0}.tmi.twitch.tv'.format(source)
        self.arguments = [text]
        self.tags = [
            {'key': u'badges', 'value': u'broadcaster/1'},
            {'key': u'color', 'value': u'#FFFFFF'},
            {'key': u'display-name', 'value': u'{}'.format(source)},
        ]
        if emotes:
            self.tags.append({'key': u'emotes', 'value': u'25:0-4'})
        if bits:
            self.tags.append({'key': u'bits', 'value': u'20'})


class TestTwitch(threading.Thread):
    def __init__(self, main_class):
        super(TestTwitch, self).__init__()
        self.main_class = main_class  # type: Twitch
        self.main_class.rest_add('POST', 'push_message', self.send_message)
        self.tw_queue = None

    def run(self):
        while True:
            try:
                thread = self.main_class.channels.items()[0][1]
                if thread.irc.twitch_queue:
                    self.tw_queue = thread.irc.twitch_queue
                    break
            except:
                continue
        log.info("twitch Testing mode online")

    def send_message(self, *args, **kwargs):
        emotes = kwargs.get('emotes', False)
        bits = kwargs.get('bits', False)
        nickname = kwargs.get('nickname', 'super_tester')
        text = kwargs.get('text', 'Kappa 123')

        self.tw_queue.put(TwitchMessage(nickname, text, emotes, bits))


class Twitch(ChatModule):
    def __init__(self, *args, **kwargs):
        log.info("Initializing twitch chat")
        ChatModule.__init__(self, *args, **kwargs)

        self.host = CONF_DICT['config']['host']
        self.port = int(CONF_DICT['config']['port'])
        self.bttv = CONF_DICT['config']['bttv']
        self.access_code = self._conf_params['config'].get('access_code')
        if self.access_code:
            headers['Authorization'] = 'OAuth {}'.format(self.access_code)

        self.rest_add('GET', 'oidc', self.parse_oidc_request)
        self.rest_add('POST', 'oidc', self.oidc_code)

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self, *args, **kwargs):
        return CONF_GUI

    def _test_class(self):
        return TestTwitch(self)

    def load_module(self, *args, **kwargs):
        ChatModule.load_module(self, *args, **kwargs)
        if 'webchat' in self._loaded_modules:
            self._loaded_modules['webchat']['class'].add_depend('twitch')
        self._conf_params['settings']['remove_text'] = self.get_remove_text()

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

    def _add_channel(self, chat):
        ChatModule.add_channel(self, chat)
        self.channels[chat] = TWThread(self.queue, self.host, self.port, chat, self.bttv,
                                       settings=self._conf_params['settings'], chat_module=self)
        self.channels[chat].start()

    def apply_settings(self, **kwargs):
        if 'webchat' in kwargs.get('from_depend', []):
            self._conf_params['settings']['remove_text'] = self.get_remove_text()
        ChatModule.apply_settings(self, **kwargs)

    def parse_oidc_request(self, req):
        return '<script>' \
               'var http = new XMLHttpRequest();' \
               'var params = "request=" + encodeURIComponent(window.location.hash);' \
               'http.open("POST", "oidc", true);' \
               'http.setRequestHeader("Content-type", "application/x-www-form-urlencoded");' \
               'http.send(params);' \
               '</script>'

    def oidc_code(self, req, **kwargs):
        def remove_hash(item):
            return item if '#' not in item else item[1:]
        items_list = map(remove_hash, kwargs.get('request').split('&'))
        item_dict = {}
        for item in items_list:
            item_dict[item.split('=')[0]] = item.split('=')[1]

        if not self.access_code:
            self.access_code = item_dict['access_token']
            self._conf_params['config']['access_code'] = self.access_code

            headers['Authorization'] = 'OAuth {}'.format(self.access_code)
        if self.channels:
            self.api_call('channels/{}/editors'.format(self.channels.items()[0][0]))
        return 'Access Code saved'

    def api_call(self, key):
        req = requests.get(API_URL.format(key), headers=headers)
        if req.ok:
            return req.json()
        raise TwitchAPIError('Unable to get {}'.format(key))

    def register_iodc(self, parent_window):
        port = self._loaded_modules['webchat']['port']

        url = 'https://api.twitch.tv/kraken/oauth2/authorize?client_id={}' \
              '&redirect_uri={}' \
              '&response_type={}' \
              '&scope={}'.format(headers['Client-ID'], 'http://localhost:{}/{}'.format(port, 'rest/twitch/oidc'),
                                 'token', 'channel_editor channel_read')
        request = requests.get(url)

        if request.ok:
            parent_window.create_browser(request.url)
        pass
