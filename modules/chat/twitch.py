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
from modules.helper.module import ChatModule, Channel, CHANNEL_ONLINE, CHANNEL_OFFLINE, CHANNEL_PENDING
from modules.helper.system import translate_key, EMOTE_FORMAT, NO_VIEWERS, register_iodc
from modules.interface.types import LCStaticBox, LCPanel, LCText, LCBool, LCButton

logging.getLogger('irc').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('twitch')
headers = {'Client-ID': '5jwove9dketiiz2kozapz8rhjdsxqxc'}
headers_v5 = {'Client-ID': '5jwove9dketiiz2kozapz8rhjdsxqxc',
              'Accept': 'application/vnd.twitchtv.v5+json'}
BITS_THEME = 'dark'
BITS_TYPE = 'animated'
BITS_SCALE = '4'
EMOTE_SMILE_URL = 'http://static-cdn.jtvnw.net/emoticons/v1/{id}/1.0'
NOT_FOUND = 'none'
SOURCE = 'tw'
SOURCE_ICON = 'https://www.twitch.tv/favicon.ico'
FILE_ICON = os.path.join('img', 'tw.png')
SYSTEM_USER = 'Twitch.TV'
BITS_REGEXP = r'(\D+)(\d+)'
API_URL = 'https://api.twitch.tv/kraken/{}'

PING_DELAY = 10

CONF_DICT = LCPanel(icon=FILE_ICON)
CONF_DICT['config'] = LCStaticBox()
CONF_DICT['config']['host'] = LCText('irc.twitch.tv')
CONF_DICT['config']['port'] = LCText(6667)
CONF_DICT['config']['show_pm'] = LCBool(True)
CONF_DICT['config']['bttv'] = LCBool(True)
CONF_DICT['config']['frankerz'] = LCBool(True)
CONF_DICT['config']['show_channel_names'] = LCBool(True)
CONF_DICT['config']['show_nickname_colors'] = LCBool(True)
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

CONNECTION_SUCCESS = translate_key(MODULE_KEY.join(['twitch', 'connection_success']))
CONNECTION_DIED = translate_key(MODULE_KEY.join(['twitch', 'connection_died']))
CONNECTION_CLOSED = translate_key(MODULE_KEY.join(['twitch', 'connection_closed']))
CONNECTION_JOINING = translate_key(MODULE_KEY.join(['twitch', 'joining']))
CHANNEL_JOIN_SUCCESS = translate_key(MODULE_KEY.join(['twitch', 'join_success']))
CHANNEL_JOINING = translate_key(MODULE_KEY.join(['twitch', 'joining']))


def _parse_msg(msg):
    return TwitchMessage(msg)


class TwitchUserError(Exception):
    """Exception for twitch user error"""


class TwitchNormalDisconnect(Exception):
    """Normal Disconnect exception"""


class TwitchAPIError(Exception):
    """Exception of API"""


class TwitchMessage(object):
    def __init__(self, msg):
        self.arguments = msg.arguments
        self.source = msg.source
        self.tags = {tag['key']: tag['value'] for tag in msg.tags if tag['value']}
        self.type = msg.type


class TwitchTextMessage(TextMessage):
    def __init__(self, msg, me, sub_message):
        self.tags = msg.tags
        self.bits = {}
        user = msg.tags['display-name'] if 'display-name' in msg.tags else msg.source.split('!')[0]
        TextMessage.__init__(self, platform_id=SOURCE, icon=SOURCE_ICON,
                             user=user, text=msg.arguments.pop(), me=me, sub_message=sub_message)


class TwitchSystemMessage(SystemMessage):
    def __init__(self, text, category='system', **kwargs):
        SystemMessage.__init__(self, text, platform_id=SOURCE, icon=SOURCE_ICON,
                               user=SYSTEM_USER, category=category, **kwargs)


class TwitchMessageHandler(threading.Thread):
    def __init__(self, queue, twitch_queue, **kwargs):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.message_queue = queue
        self.twitch_queue = twitch_queue
        self.source = SOURCE

        self.irc_class = kwargs.get('irc_class')  # type: IRC
        self.nick = kwargs.get('nick')
        self.badges = kwargs.get('badges')
        self.custom_smiles = kwargs.get('custom_smiles', {})
        self.custom_badges = kwargs.get('custom_badges')
        self.bits = self._reformat_bits(kwargs.get('bits'))

        self.chat_module = kwargs.get('chat_module')
        self.kwargs = kwargs

        self.message_functions = {
            'pubmsg': self._handle_message,
            'action': self._handle_action,
            'clearchat': self._handle_clearchat,
            'usernotice': self._handle_usernotice
        }
        self.usernotice_functions = {
            'sub': self._handle_sub,
            'resub': self._handle_sub,
            'subgift': self._handle_subgift,
            'anonsubgift': self._handle_subgift,
            'raid': self._handle_raid,
            'ritual': self._handle_ritual
        }

    def run(self):
        while True:
            self.process_message(self.twitch_queue.get())

    def process_message(self, recv_msg):
        # After we receive the message we have to process the tags
        # There are multiple things that are available, but
        #  for now we use only display-name, which is case-able.
        # Also, there is slight problem with some users, they don't have
        #  the display-name tag, so we have to check their "real" username
        #  and capitalize it because twitch does so, so we do the same.
        msg = _parse_msg(recv_msg)
        if msg.type in self.message_functions:
            self.message_functions[msg.type](msg)

    def _handle_action(self, msg):
        self._handle_message(msg, me=True)

    def _handle_badges(self, message):
        for badge in message.tags['badges'].split(','):
            badge_tag, badge_size = badge.split('/')
            # Fix some of the names
            badge_tag = badge_tag.replace('moderator', 'mod')

            if badge_tag in self.custom_badges:
                badge_info = self.custom_badges.get(badge_tag)['versions'][badge_size]
                for key in ['image_url_4x', 'image_url_2x', 'image_url_1x']:
                    if key in badge_info:
                        break
                url = badge_info.get(key)
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
            message.add_badge(badge_tag, url)

    @staticmethod
    def _handle_emotes(message):
        conveyor_emotes = []
        for emote in message.tags['emotes'].split('/'):
            emote_id, emote_pos_diap = emote.split(':')

            for position in emote_pos_diap.split(','):
                start, end = position.split('-')
                conveyor_emotes.append({'emote_id': emote_id,
                                        'start': int(start),
                                        'end': int(end)})
        conveyor_emotes = sorted(conveyor_emotes, key=lambda k: k['start'], reverse=True)

        for emote in conveyor_emotes:
            message.text = u'{start}{emote}{end}'.format(start=message.text[:emote['start']],
                                                         end=message.text[emote['end'] + 1:],
                                                         emote=EMOTE_FORMAT.format(emote['emote_id']))
            message.add_emote(emote['emote_id'], EMOTE_SMILE_URL.format(id=emote['emote_id']))

    def _handle_custom_emotes(self, message):
        words = message.text.split()
        for index, word in enumerate(words):
            if word in self.custom_smiles:
                custom_smile = self.custom_smiles[word]
                message.add_emote(custom_smile['key'], custom_smile['url'])
                words[index] = EMOTE_FORMAT.format(custom_smile['key'])
        message.text = ' '.join(words)

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

    def _handle_sub(self, msg):
        if 'system-msg' in msg.tags:
            msg_text = msg.tags['system-msg']
            self.irc_class.system_message(msg_text, category='chat', sub_message=True)
        if msg.arguments:
            self._handle_message(msg, sub_message=True)

    def _handle_subgift(self, msg):
        self._handle_sub(msg)

    def _handle_raid(self, msg):
        channel_image = msg.tags['msg-param-profileImageURL']
        display_name = msg.tags['msg-param-displayName']
        viewer_count = msg.tags['msg-param-viewerCount']
        translate_text = translate_key('twitch.raid').format(display_name, viewer_count)
        self.irc_class.system_message(translate_text, category='chat', sub_message=True,
                                      badges=[Badge('raid', channel_image)])

    def _handle_ritual(self, msg):
        pass

    def _handle_usernotice(self, msg):
        if msg.tags['msg-id'] in self.usernotice_functions:
            self.usernotice_functions[msg.tags['msg-id']](msg)

    def _handle_message(self, msg, sub_message=False, me=False):
        message = TwitchTextMessage(msg, me, sub_message)
        if message.user == 'twitchnotify':
            self.irc_class.queue.put(TwitchSystemMessage(message.text, category='chat'))

        if 'badges' in msg.tags:
            self._handle_badges(message)
        if 'emotes' in msg.tags:
            self._handle_emotes(message)
        if 'bits' in msg.tags:
            self._handle_bits(message)
        if 'color' in msg.tags:
            self._handle_viewer_color(message)

        self._handle_custom_emotes(message)
        self._handle_pm(message)
        self._send_message(message)

    def _handle_viewer_color(self, message):
        if self.irc_class.chat_module.conf_params()['config']['config']['show_nickname_colors']:
            message.nick_colour = message.tags['color']

    def _handle_bits(self, message):
        for word in message.text.split():
            reg = re.match(BITS_REGEXP, word)
            if not reg:
                continue

            emote, amount = reg.groups()
            tier = min([tier for tier in self.bits[emote]['tiers'].keys() if tier - int(amount) <= 0],
                       key=lambda x: (abs(x - int(amount)), x))

            emote_key = '{}-{}'.format(emote, tier)
            if emote_key in message.bits:
                continue

            message.bits[emote_key] = self.bits[emote]['tiers'][tier]
            message.text = message.text.replace(emote, EMOTE_FORMAT.format(emote))

    @staticmethod
    def _handle_sub_message(message):
        message.sub_message = True
        message.jsonable += ['sub_message']

    def _send_message(self, message):
        self._post_process_multiple_channels(message)
        self._post_process_bits(message)
        self.message_queue.put(message)

    @staticmethod
    def _post_process_bits(message):
        if not message.bits:
            return
        for emote_key, bit in message.bits.items():
            emote = emote_key.split('-')[0]
            message.add_emote(emote, bit['images'][BITS_THEME][BITS_TYPE][BITS_SCALE])

    def _post_process_multiple_channels(self, message):
        channel_class = self.irc_class.main_class
        if channel_class.chat_module.conf_params()['config']['config']['show_channel_names']:
            message.channel_name = channel_class.display_name

    @staticmethod
    def _reformat_bits(bits):
        return {
            prefix: {
                'tiers': {int(tier['id']): tier for tier in data['tiers']},
                'states': data['states'],
                'scales': data['scales']
            } for prefix, data in bits.items()
        }


class TwitchPingHandler(threading.Thread):
    def __init__(self, irc_connection, main_class, irc_class):
        threading.Thread.__init__(self)
        self.irc_connection = irc_connection
        self.main_class = main_class
        self.irc_class = irc_class

    def run(self):
        log.info("Ping started")
        while self.irc_connection.connected:
            self.irc_connection.ping("keep-alive")
            try:
                self.main_class.viewers = self.main_class.get_viewers()
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

    def system_message(self, message, category='system', **kwargs):
        self.queue.put(TwitchSystemMessage(message, category=category, channel_name=self.nick, **kwargs))

    def on_disconnect(self, connection, event):
        if 'CLOSE_OK' in event.arguments:
            log.info("Connection closed")
            self.system_message(CONNECTION_CLOSED.format(self.nick), category='connection')
            raise TwitchNormalDisconnect()
        else:
            log.info("Connection lost")
            log.debug("connection: {}".format(connection))
            log.debug("event: {}".format(event))
            self.main_class.status = CHANNEL_OFFLINE
            self.system_message(CONNECTION_DIED.format(self.nick), category='connection')
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
        self.system_message(CHANNEL_JOINING.format(self.channel),
                            category='connection')
        # After we receive IRC Welcome we send request for join and
        #  request for Capabilities (Twitch color, Display Name,
        #  Subscriber, etc)
        connection.join(self.channel)
        connection.cap('REQ', ':twitch.tv/tags')
        connection.cap('REQ', ':twitch.tv/commands')
        ping_handler = TwitchPingHandler(connection, self.main_class, self)
        ping_handler.start()

    def on_join(self, connection, event):
        log.debug("connection: {}".format(connection))
        log.debug("event: {}".format(event))
        msg = CHANNEL_JOIN_SUCCESS.format(self.channel)
        self.main_class.status = CHANNEL_ONLINE
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


class TWChannel(threading.Thread, Channel):
    def __init__(self, queue, host, port, channel, anon=True, **kwargs):
        threading.Thread.__init__(self)
        Channel.__init__(self, channel)

        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = True
        self.queue = queue

        self.host = host
        self.port = port
        self.custom_smiles = {}

        self.bttv = kwargs.get('bttv')
        self.frankerz = kwargs.get('frankerz')

        self.kwargs = kwargs
        self.chat_module = kwargs.get('chat_module')
        self.display_name = None
        self.channel_id = None
        self.irc = None

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
                self._status = CHANNEL_PENDING
                if self.load_config():
                    self.irc = IRC(
                        self.queue, self.channel, main_class=self, custom_smiles=self.custom_smiles,
                        **self.kwargs)
                    self.irc.connect(self.host, self.port, self.nickname)
                    self._status = CHANNEL_ONLINE
                    self.irc.start()
                    log.info("Connection closed")
                    break
            except TwitchUserError:
                log.critical("Unable to find twitch user, please fix")
                self._status = CHANNEL_OFFLINE
                break
            except TwitchNormalDisconnect:
                log.info("Twitch closing")
                self._status = CHANNEL_OFFLINE
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
            if self.bttv:
                request = requests.get("https://api.betterttv.net/emotes", timeout=10)
                if request.status_code == 200:
                    for smile in request.json()['emotes']:
                        self.custom_smiles[smile['regex']] = {
                            'key': smile['regex'],
                            'url': 'https:{}'.format(smile['url'])
                        }
                else:
                    raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get BTTV smiles, error {0}\nArgs: {1}".format(exc.message, exc.args))

        try:
            # Getting FrankerZ smiles
            if self.frankerz:
                request = requests.get("https://api.frankerfacez.com/v1/room/id/{}".format(self.channel_id), timeout=10)
                if request.status_code == 200:
                    req_json = request.json()
                    for set_name, s_set in req_json['sets'].items():
                        for smile in s_set['emoticons']:
                            urls = smile['urls']
                            url = urls.get('4', urls.get('2', urls.get('1')))
                            self.custom_smiles[smile['name']] = {
                                'key': smile['name'],
                                'url': 'https:{}'.format(url)
                            }
                else:
                    raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get FrankerZ smiles, error {0}\nArgs: {1}".format(exc.message, exc.args))

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

        try:
            bits_url = "https://api.twitch.tv/kraken/bits/actions/?channel_id={}"
            request = requests.get(bits_url.format(self.channel_id), headers=headers_v5)
            if request.status_code == 200:
                data = request.json()['actions']
                self.kwargs['bits'] = {item['prefix'].lower(): item for item in data}
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get twitch undocumented api badges, error {0}\n"
                        "Args: {1}".format(exc.message, exc.args))

        return True

    def stop(self):
        try:
            self.irc.tw_connection.disconnect("CLOSE_OK")
        except TwitchNormalDisconnect:
            pass

    def get_viewers(self):
        streams_url = 'https://api.twitch.tv/kraken/streams/{0}'.format(self.channel)
        try:
            request = requests.get(streams_url, headers=headers)
            if request.status_code == 200:
                json_data = request.json()
                if json_data['stream']:
                    return request.json()['stream'].get('viewers', NO_VIEWERS)
                return NO_VIEWERS
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get user count, error {0}\nArgs: {1}".format(exc.message, exc.args))


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

        self.tw_queue.put({})


class Twitch(ChatModule):
    def __init__(self, *args, **kwargs):
        log.info("Initializing twitch chat")
        ChatModule.__init__(self, *args, **kwargs)

        self.host = CONF_DICT['config']['host']
        self.port = int(CONF_DICT['config']['port'])
        self.bttv = CONF_DICT['config']['bttv']
        self.frankerz = CONF_DICT['config']['frankerz']
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

    def _add_channel(self, chat):
        self.channels[chat] = TWChannel(self.queue, self.host, self.port, chat, bttv=self.bttv, frankerz=self.frankerz,
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
