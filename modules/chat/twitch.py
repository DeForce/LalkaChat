# Copyright (C) 2016   CzT/Vladislav Ivanov
import queue
import logging.config
import os
import random
import re
import threading
import time

import irc.client
import requests

from modules.gui import MODULE_KEY
from modules.helper.message import TextMessage, SystemMessage, Badge, RemoveMessageByUsers, DEFAULT_MESSAGE_TYPE, \
    SUBSCRIBE_MESSAGE_TYPE, HIGHLIGHT_MESSAGE_TYPE
from modules.helper.module import ChatModule, Channel, CHANNEL_ONLINE, CHANNEL_OFFLINE, CHANNEL_PENDING, \
    CHANNEL_DISABLED
from modules.helper.system import translate_key, EMOTE_FORMAT, NO_VIEWERS, get_wx_parent, get_secret
from modules.interface.types import LCStaticBox, LCPanel, LCText, LCBool, LCButton

logging.getLogger('irc').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('twitch')
headers = {'Client-ID': get_secret('twitch.clientid'),
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
API_URL = 'https://api.twitch.tv/kraken'

BTTV_URL = 'https://cdn.betterttv.net/emote/{id}/1x'

PING_DELAY = 10


def register_iodc(event):
    parent = get_wx_parent(event.GetEventObject()).Parent
    twitch = parent.loaded_modules.get('twitch')['class']
    if not twitch:
        raise ValueError('Unable to find loaded Twitch.TV Module')

    twitch.register_iodc(parent)
    pass


CONF_DICT = LCPanel(icon=FILE_ICON)
CONF_DICT['config'] = LCStaticBox()
CONF_DICT['config']['host'] = LCText('irc.twitch.tv')
CONF_DICT['config']['port'] = LCText(6667)
CONF_DICT['config']['show_pm'] = LCBool(True)
CONF_DICT['config']['bttv'] = LCBool(True)
CONF_DICT['config']['frankerz'] = LCBool(True)
CONF_DICT['config']['show_channel_names'] = LCBool(False)
CONF_DICT['config']['show_nickname_colors'] = LCBool(True)
CONF_DICT['config']['register_oidc'] = LCButton(register_iodc)

CONF_GUI = {
    'config': {
        'hidden': ['host', 'port'],
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
    def __init__(self, msg, me, message_type):
        user = msg.tags['display-name'] if 'display-name' in msg.tags else msg.source.split('!')[0]
        super().__init__(platform_id=SOURCE, icon=SOURCE_ICON, user=user, text=msg.arguments.pop(),
                         me=me, message_type=message_type)
        self.tags = msg.tags
        self.msg_id = self.tags.get('msg-id')
        self.bits = {}


class TwitchMessageHandler(threading.Thread):
    def __init__(self, twitch_queue, irc_class=None, channel_class=None, nick=None,
                 badges=None, custom_smiles=None, chat_module=None, bits=None, **kwargs):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.twitch_queue = twitch_queue
        self.source = SOURCE

        self.irc_class: IRC = irc_class
        self.channel_class: TWChannel = channel_class
        self.nick = nick
        self.badges = badges
        self.custom_smiles = custom_smiles
        self.bits = self._reformat_bits(bits)

        self.chat_module = chat_module
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
        msg = TwitchMessage(recv_msg)
        if msg.type in self.message_functions:
            self.message_functions[msg.type](msg)

    def _handle_action(self, msg):
        self._handle_message(msg, me=True)

    def _handle_badges(self, message):
        for badge in message.tags['badges'].split(','):
            badge_tag, badge_size = badge.split('/')

            if badge_tag in self.badges:
                badge_info = self.badges.get(badge_tag)[badge_size]
                url = badge_info.get('image')
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
        if re.match(f'^@?{self.nick}[ ,]?', message.text.lower()):
            if self.chat_module.get_config()['config'].get('show_pm'):
                message.pm = True

    def _handle_clearchat(self, msg):
        self.channel_class.put_message(RemoveMessageByUsers(msg.arguments, platform=SOURCE))

    def _handle_sub(self, msg):
        if 'system-msg' in msg.tags:
            msg_text = msg.tags['system-msg']
            self.channel_class.put_system_message(msg_text, message_type=SUBSCRIBE_MESSAGE_TYPE)
        if msg.arguments:
            self._handle_message(msg, sub_message=True)

    def _handle_subgift(self, msg):
        self._handle_sub(msg)

    def _handle_raid(self, msg):
        channel_image = msg.tags['msg-param-profileImageURL']
        display_name = msg.tags['msg-param-displayName']
        viewer_count = msg.tags['msg-param-viewerCount']
        translate_text = translate_key('twitch.raid').format(display_name, viewer_count)
        self.channel_class.put_system_message(translate_text, message_type=SUBSCRIBE_MESSAGE_TYPE,
                                              badges=[Badge('raid', channel_image)])

    def _handle_ritual(self, msg):
        log.info(f'Ritual: {msg}')

    def _handle_usernotice(self, msg):
        if msg.tags['msg-id'] in self.usernotice_functions:
            self.usernotice_functions[msg.tags['msg-id']](msg)

    def _handle_message(self, msg, sub_message=False, me=False):
        message_type = SUBSCRIBE_MESSAGE_TYPE if sub_message else DEFAULT_MESSAGE_TYPE

        message: TwitchTextMessage = self.channel_class.create_message(msg, me, message_type=message_type)
        if message.user == 'twitchnotify':
            self.channel_class.put_system_message(message.text)

        if 'badges' in msg.tags:
            self._handle_badges(message)
        if 'bits' in msg.tags:
            self._handle_bits(message)
        if 'emotes' in msg.tags:
            self._handle_emotes(message)
        if 'color' in msg.tags:
            self._handle_viewer_color(message)

        self._handle_channel_points(message)

        self._handle_custom_emotes(message)
        self._handle_pm(message)
        self._send_message(message)

    def _handle_viewer_color(self, message):
        if self.chat_module.get_config('config', 'show_nickname_colors'):
            message.nick_colour = message.tags['color']

    def _handle_bits(self, message):
        for word in message.text.split():
            reg = re.match(BITS_REGEXP, word)
            if not reg:
                continue

            emote, amount = reg.groups()
            emote = emote.lower()
            if emote not in self.bits:
                log.info('key %s not in bits', emote)
                continue
            tier = min([tier for tier in self.bits[emote]['tiers'].keys() if tier - int(amount) <= 0],
                       key=lambda x: (abs(x - int(amount)), x))

            emote_key = f'{emote}-{tier}'
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
        self.channel_class.put_message(message)

    @staticmethod
    def _post_process_bits(message):
        if not message.bits:
            return
        for emote_key, bit in message.bits.items():
            emote = emote_key.split('-')[0]
            message.add_emote(emote, bit['images'][BITS_THEME][BITS_TYPE][BITS_SCALE])

    def _post_process_multiple_channels(self, message):
        if self.chat_module.get_config('config', 'show_channel_names'):
            message.channel_name = self.channel_class.display_name

    @staticmethod
    def _reformat_bits(bits):
        return {
            prefix: {
                'tiers': {int(tier['id']): tier for tier in data['tiers']},
                'states': data['states'],
                'scales': data['scales']
            } for prefix, data in bits.items()
        }

    def _handle_channel_points(self, message):
        if message.msg_id:
            log.info(f'msg_id: {message.msg_id}')
        if message.msg_id == 'highlighted-message':
            message.message_type = HIGHLIGHT_MESSAGE_TYPE


class TwitchPingHandler(threading.Thread):
    def __init__(self, irc_connection, channel_class, irc_class):
        threading.Thread.__init__(self)
        self.irc_connection = irc_connection
        self.channel_class = channel_class
        self.irc_class = irc_class

    def run(self):
        log.info("Ping started")
        while self.irc_connection.connected:
            self.irc_connection.ping("keep-alive")
            try:
                self.channel_class.viewers = self.channel_class.get_viewers()
            except Exception as exc:
                log.exception(exc)
            time.sleep(PING_DELAY)


class IRC(irc.client.SimpleIRCClient):
    def __init__(self, channel, channel_class=None, chat_module=None, **kwargs):
        irc.client.SimpleIRCClient.__init__(self)
        # Basic variables, twitch channel are IRC so #channel
        self.channel = "#" + channel.lower()
        self.nick = channel.lower()
        self.twitch_queue = queue.Queue()
        self.tw_connection = None
        self.channel_class = channel_class
        self.chat_module = chat_module

        self.msg_handler = TwitchMessageHandler(self.twitch_queue,
                                                nick=self.nick,
                                                irc_class=self,
                                                channel_class=self.channel_class,
                                                chat_module=self.chat_module,
                                                **kwargs)
        self.msg_handler.start()

    def on_disconnect(self, connection, event):
        if 'CLOSE_OK' in event.arguments:
            log.info("Connection closed")
            self.chat_module.put_system_message(CONNECTION_CLOSED.format(self.nick))
            raise TwitchNormalDisconnect()
        else:
            log.info("Connection lost")
            log.debug("connection: %s", connection)
            log.debug("event: %s", event)
            self.channel_class.status = CHANNEL_OFFLINE
            self.channel_class.put_system_message(CONNECTION_DIED.format(self.nick))
            timer = threading.Timer(5.0, self.reconnect,
                                    args=[self.channel_class.host, self.channel_class.port,
                                          self.channel_class.nickname])
            timer.start()

    def reconnect(self, host, port, nickname):
        try_count = 0
        while True:
            try_count += 1
            log.info("Reconnecting, try %s", try_count)
            try:
                self.connect(host, port, nickname)
                break
            except Exception as exc:
                log.exception(exc)

    def on_welcome(self, connection, event):
        log.info("Welcome Received, joining %s channel", self.channel)
        log.debug("event: %s", event)
        self.tw_connection = connection
        self.channel_class.put_system_message(CHANNEL_JOINING.format(self.channel))
        # After we receive IRC Welcome we send request for join and
        #  request for Capabilities (Twitch color, Display Name,
        #  Subscriber, etc)
        connection.join(self.channel)
        connection.cap('REQ', ':twitch.tv/tags')
        connection.cap('REQ', ':twitch.tv/commands')
        ping_handler = TwitchPingHandler(connection, self.channel_class, self)
        ping_handler.start()

    def on_join(self, connection, event):
        log.debug("connection: %s", connection)
        log.debug("event: %s", event)
        msg = CHANNEL_JOIN_SUCCESS.format(self.channel)
        self.channel_class.status = CHANNEL_ONLINE
        log.info(msg)
        self.channel_class.put_system_message(msg)

    def on_pubmsg(self, connection, event):
        log.debug("connection: %s", connection)
        log.debug("event: %s", event)
        self.twitch_queue.put(event)

    def on_action(self, connection, event):
        log.debug("connection: %s", connection)
        log.debug("event: %s", event)
        self.twitch_queue.put(event)

    def on_clearchat(self, connection, event):
        log.debug("connection: %s", connection)
        log.debug("event: %s", event)
        self.twitch_queue.put(event)

    def on_usernotice(self, connection, event):
        log.debug("connection: %s", connection)
        log.debug("event: %s", event)
        self.twitch_queue.put(event)


class TWChannel(threading.Thread, Channel):
    def __init__(self, m_queue, host, port, channel, anon=True, chat_module=None, **kwargs):
        threading.Thread.__init__(self)
        Channel.__init__(self, channel, m_queue, icon=SOURCE_ICON, platform_id=SOURCE, system_user=SYSTEM_USER)

        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = True

        self.host = host
        self.port = port
        self.custom_smiles = {}
        self.badges = {}
        self.bits = {}

        self.bttv = kwargs.get('bttv')
        self.frankerz = kwargs.get('frankerz')

        self.kwargs = kwargs
        self.chat_module = chat_module
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

    def create_message(self, msg, me, message_type):
        return TwitchTextMessage(msg, me, message_type)

    def run(self):
        try_count = 0
        # We are connecting via IRC handler.
        while True:
            try_count += 1
            try:
                if self._status == CHANNEL_DISABLED:
                    break

                log.info("Connecting, try %s", try_count)
                self._status = CHANNEL_PENDING
                if self.load_config():
                    self.irc = IRC(self.channel, channel_class=self, chat_module=self.chat_module,
                                   custom_smiles=self.custom_smiles, badges=self.badges, bits=self.bits, **self.kwargs)
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
        request = requests.get(f'{API_URL}/users', params={'login': self.channel}, headers=headers)
        if request.ok:
            data = request.json()
            if len(data['users']) > 1:
                log.error('Multiple Users found, that is an issue, verify user name')
            user = data['users'][0]
            self.display_name = user['display_name']
            self.channel_id = user['_id']
        else:
            log.error('Unable to get channel ID, error: %s\nArgs: %s')
            return False

        try:
            # Getting random IRC server to connect to
            request = requests.get(f"http://tmi.twitch.tv/servers?channel={self.channel}", headers=headers)
            if request.ok:
                self.host = random.choice(request.json()['servers']).split(':')[0]
            else:
                raise Exception(f"Not successful status code: {request.status_code}")
        except Exception as exc:
            log.error(f"Unable to get server list, error: {exc}\nArgs: {exc.args}")
            return False

        try:
            # Getting Better Twitch TV smiles
            if self.bttv:
                request = requests.get("https://api.betterttv.net/2/emotes", timeout=10)
                if request.ok:
                    for smile in request.json()['emotes']:
                        self.custom_smiles[smile['code']] = {
                            'key': smile['code'],
                            'url': BTTV_URL.format(id=smile['id'])
                        }
                else:
                    raise Exception(f"Not successful status code: {request.status_code}")
        except Exception as exc:
            log.warning(f"Unable to get BTTV smiles, error {exc}\nArgs: {exc.args}")

        try:
            # Getting FrankerZ smiles
            if self.frankerz:
                request = requests.get(f"https://api.frankerfacez.com/v1/room/id/{self.channel_id}", timeout=10)
                if request.ok:
                    req_json = request.json()
                    for set_name, s_set in req_json['sets'].items():
                        for smile in s_set['emoticons']:
                            urls = smile['urls']
                            url = urls.get('4', urls.get('2', urls.get('1')))
                            self.custom_smiles[smile['name']] = {
                                'key': smile['name'],
                                'url': f'https:{url}'
                            }
                else:
                    raise Exception(f"Not successful status code: {request.status_code}")
        except Exception as exc:
            log.warning(f"Unable to get FrankerZ smiles, error {exc}\nArgs: {exc.args}")

        try:
            # Warning, undocumented, can change a LOT
            # Getting CUSTOM twitch badges
            request = requests.get("https://badges.twitch.tv/v1/badges/global/display")
            if request.ok:
                for badge, badge_config in request.json()['badge_sets'].items():
                    self.badges[badge] = {
                        version: {
                            'image': v.get('image_url_4x', v.get('image_url_2x', v.get('image_url_1x')))
                        } for version, v in badge_config['versions'].items()
                    }
            else:
                raise Exception(f"Not successful status code: {request.status_code}")
        except Exception as exc:
            log.warning(f"Unable to get twitch undocumented api badges, error {exc}\nArgs: {exc.args}")

        try:
            # Warning, undocumented, can change a LOT
            # Getting CUSTOM twitch badges
            badges_url = "https://badges.twitch.tv/v1/badges/channels/{0}/display"
            request = requests.get(badges_url.format(self.channel_id))
            if request.ok:
                for badge, badge_config in request.json()['badge_sets'].items():
                    processed_badge = {
                        version: {
                            'image': v.get('image_url_4x', v.get('image_url_2x', v.get('image_url_1x')))
                        } for version, v in badge_config['versions'].items()
                    }

                    if badge in self.badges:
                        self.badges[badge].update(processed_badge)
                    else:
                        self.badges[badge] = processed_badge
            else:
                raise Exception(f"Not successful status code: {request.status_code}")
        except Exception as exc:
            log.warning(f"Unable to get twitch undocumented api badges, error {exc}\nArgs: {exc.args}")

        try:
            bits_url = f"https://api.twitch.tv/kraken/bits/actions/?channel_id={self.channel_id}"
            request = requests.get(bits_url, headers=headers)
            if request.status_code == 200:
                data = request.json()['actions']
                self.bits = {item['prefix'].lower(): item for item in data}
            else:
                raise Exception("Not successful status code: %s", request.status_code)
        except Exception as exc:
            log.warning(f"Unable to get twitch undocumented api badges, error {exc}\nArgs: {exc.args}")

        return True

    def stop(self):
        try:
            self._status = CHANNEL_DISABLED
            self.irc.tw_connection.disconnect("CLOSE_OK")
        except TwitchNormalDisconnect:
            pass

    def get_viewers(self):
        streams_url = f'https://api.twitch.tv/kraken/streams/{self.channel_id}'
        try:
            request = requests.get(streams_url, headers=headers)
            if request.status_code == 200:
                json_data = request.json()
                if json_data['stream']:
                    return request.json()['stream'].get('viewers', NO_VIEWERS)
                return NO_VIEWERS
            else:
                raise Exception(f"Not successful status code: {request.status_code}")
        except Exception as exc:
            log.warning(f"Unable to get user count, error {exc}\nArgs: {exc.args}")


class Twitch(ChatModule):
    def __init__(self, *args, **kwargs):
        log.info("Initializing twitch chat")
        ChatModule.__init__(self, config=CONF_DICT, gui=CONF_GUI, *args, **kwargs)

        self.host = CONF_DICT['config']['host']
        self.port = int(CONF_DICT['config']['port'])
        self.bttv = CONF_DICT['config']['bttv']
        self.frankerz = CONF_DICT['config']['frankerz']
        self.access_code = self.get_config('access_code')
        if self.access_code:
            headers['Authorization'] = f'OAuth {self.access_code}'

        self.rest_add('GET', 'oidc', self.parse_oidc_request)
        self.rest_add('POST', 'oidc', self.oidc_code)

    def _add_channel(self, chat):
        self.channels[chat] = TWChannel(self.queue, self.host, self.port, chat, bttv=self.bttv, frankerz=self.frankerz,
                                        settings=self._conf_params['settings'], chat_module=self)
        self.channels[chat].start()

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

            headers['Authorization'] = f'OAuth {self.access_code}'
        if self.channels:
            self.api_call(f'channels/{self.channels.items()[0][0]}/editors')
        return 'Access Code saved'

    def api_call(self, key):
        req = requests.get(f'{API_URL}/{key}', headers=headers)
        if req.ok:
            return req.json()
        raise TwitchAPIError(f'Unable to get {key}')

    def register_iodc(self, parent_window):
        port = self._loaded_modules['webchat']['port']

        url = f'https://api.twitch.tv/kraken/oauth2/authorize?client_id={headers["Client-ID"]}' \
              f'&redirect_uri=http://localhost:{port}/rest/twitch/oidc' \
              f'&response_type=token' \
              f'&scope=channel_editor channel_read'
        request = requests.get(url)

        if request.ok:
            parent_window.create_browser(request.url)
        pass
