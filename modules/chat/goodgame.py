# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import Queue
import json
import logging
import os
import random
import re
import string
import threading
import time

import requests
from ws4py.client.threadedclient import WebSocketClient

from modules.gui import MODULE_KEY
from modules.helper.message import TextMessage, SystemMessage, Emote, RemoveMessageByIDs
from modules.helper.module import ChatModule, Channel, CHANNEL_ONLINE, CHANNEL_PENDING, CHANNEL_OFFLINE
from modules.helper.system import translate_key, EMOTE_FORMAT, NA_MESSAGE
from modules.interface.types import LCStaticBox, LCPanel, LCBool, LCText

logging.getLogger('requests').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
log = logging.getLogger('goodgame')
SOURCE = 'gg'
SOURCE_ICON = 'http://goodgame.ru/images/icons/favicon.png'
FILE_ICON = os.path.join('img', 'gg.png')
SYSTEM_USER = 'GoodGame'
ID_PREFIX = 'gg_{0}'
API = 'http://api2.goodgame.ru/{}'
SMILE_API = 'https://goodgame.ru/api/4/smiles'

CONF_DICT = LCPanel(icon=FILE_ICON)
CONF_DICT['config'] = LCStaticBox()
CONF_DICT['config']['show_pm'] = LCBool(True)
CONF_DICT['config']['socket'] = LCText('wss://chat.goodgame.ru/chat/websocket')
CONF_DICT['config']['show_channel_names'] = LCBool(True)
CONF_DICT['config']['use_channel_id'] = LCBool(False)
CONF_DICT['config']['check_viewers'] = LCBool(True)
SMILE_REGEXP = r':(\w+|\d+):'
SMILE_FORMAT = ':{}:'

CONF_GUI = {
    'config': {
        'hidden': ['socket'],
        'channels_list': {
            'view': 'list',
            'addable': 'true'
        }
    },
    'non_dynamic': ['config.socket']
}

CONNECTION_SUCCESS = translate_key(MODULE_KEY.join(['goodgame', 'connection_success']))
CONNECTION_DIED = translate_key(MODULE_KEY.join(['goodgame', 'connection_died']))
CONNECTION_CLOSED = translate_key(MODULE_KEY.join(['goodgame', 'connection_closed']))
CONNECTION_JOINING = translate_key(MODULE_KEY.join(['goodgame', 'joining']))
CHANNEL_JOIN_SUCCESS = translate_key(MODULE_KEY.join(['goodgame', 'join_success']))

MESSAGE_WARNING = translate_key(MODULE_KEY.join(['goodgame', 'warning']))
MESSAGE_BAN = translate_key(MODULE_KEY.join(['goodgame', 'warning']))
MESSAGE_BAN_PERM = translate_key(MODULE_KEY.join(['goodgame', 'ban_permanent']))
MESSAGE_UNBAN = translate_key(MODULE_KEY.join(['goodgame', 'unban']))


class GoodgameTextMessage(TextMessage):
    def __init__(self, text, user, mid=None):
        TextMessage.__init__(self, platform_id=SOURCE, icon=SOURCE_ICON,
                             user=user, text=text, mid=mid)

    def process_smiles(self, smiles, rights, premium, prems, payments):
        smiles_array = set([item[1:-1] for item in self._text.split() if re.match(SMILE_REGEXP, item)])
        for smile in smiles_array:
            if smile not in smiles:
                continue

            smile_info = smiles.get(smile)
            allow = False
            gif = False
            if rights >= 40:
                allow = True
            elif rights >= 20 \
                    and (smile_info['channel_id'] == 0 or smile_info['channel_id'] == 10603):
                allow = True
            elif smile_info['channel_id'] == 0 or smile_info['channel_id'] == 10603:
                if not smile_info['is_premium']:
                    if smile_info['donate_lvl'] == 0:
                        allow = True
                    elif smile_info['donate_lvl'] <= int(payments):
                        allow = True
                else:
                    if premium:
                        allow = True

            for premium_item in prems:
                if smile_info['channel_id'] == premium_item:
                    if smile_info['is_premium']:
                        allow = True
                        gif = True

            if allow:
                self._text = self._text.replace(SMILE_FORMAT.format(smile), EMOTE_FORMAT.format(smile))
                url = smile_info['images']['big']
                if gif and smile_info['images']['gif']:
                    url = smile_info['images']['gif']
                self.add_emote(smile, url)


class GoodgameSystemMessage(SystemMessage):
    def __init__(self, text, category='system', **kwargs):
        SystemMessage.__init__(self, text, platform_id=SOURCE, icon=SOURCE_ICON,
                               user=SYSTEM_USER, category=category, **kwargs)


class GoodgameMessageHandler(threading.Thread):
    def __init__(self, ws_class, **kwargs):
        super(self.__class__, self).__init__()
        self.ws_class = ws_class  # type: GGChat
        self.daemon = True
        self.message_queue = kwargs.get('queue')
        self.gg_queue = kwargs.get('gg_queue')
        self.source = SOURCE

        self.nick = kwargs.get('nick')
        self.smiles = kwargs.get('smiles')
        self.main_thread = kwargs.get('main_thread')
        self.chat_module = kwargs.get('chat_module')
        self.kwargs = kwargs

    def run(self):
        while True:
            self.process_message(self.gg_queue.get())

    def process_message(self, msg):
        message_type = msg['type']
        if message_type == "message":
            self._process_message(msg)
        elif message_type == 'success_join':
            self._process_join()
        elif message_type == 'error':
            self._process_error(msg)
        elif message_type == 'user_warn':
            self._process_user_warn(msg)
        elif message_type == 'remove_message':
            self._process_remove_message(msg)
        elif message_type == 'user_ban':
            self._process_user_ban(msg)
        elif message_type == 'channel_counters':
            self._process_channel_counters()

    def _process_message(self, msg):
        # Getting all needed data from received message
        # and sending it to queue for further message handling
        message = GoodgameTextMessage(
            msg['data']['text'],
            msg['data']['user_name'],
            mid=ID_PREFIX.format(msg['data']['message_id'])
        )
        message.process_smiles(
            self.smiles,
            msg['data'].get('user_rights', 0),
            msg['data'].get('premium', 1),
            msg['data'].get('premiums', []),
            msg['data'].get('payments', '0')
        )

        if re.match('^{0},'.format(self.nick).lower(), message.text.lower()):
            if self.chat_module.conf_params()['config']['config'].get('show_pm'):
                message.pm = True
        self._send_message(message)

    def _process_join(self):
        self.ws_class.system_message(CHANNEL_JOIN_SUCCESS.format(self.nick), category='connection')

    def _process_error(self, msg):
        log.info("Received error message: {0}".format(msg))
        if msg['data']['errorMsg'] == 'Invalid channel id':
            self.ws_class.close(reason='INV_CH_ID')
            log.error("Failed to find channel on GoodGame, please check channel name")

    def _process_user_warn(self, msg):
        self.ws_class.system_message(MESSAGE_WARNING.format(
            msg['data']['moder_name'], msg['data']['user_name']), category='chat')

    def _process_remove_message(self, msg, text=None):
        if self.chat_module.conf_params()['config']['config']['show_channel_names']:
            text = self.kwargs['settings'].get('remove_text')
        remove_id = ID_PREFIX.format(msg['data']['message_id'])
        self.message_queue.put(RemoveMessageByIDs(remove_id, text=text, platform=SOURCE))

    def _process_user_ban(self, msg):
        if msg['data']['duration']:
            self.ws_class.system_message(MESSAGE_BAN.format(
                msg['data']['moder_name'],
                msg['data']['user_name'],
                msg['data']['duration']/60,
                msg['data']['reason']),
                category='chat')
        else:
            if msg['data']['permanent']:
                self.ws_class.system_message(
                    MESSAGE_BAN_PERM.format(msg['data']['moder_name'], msg['data']['user_name']),
                    category='chat')
            else:
                self.ws_class.system_message(MESSAGE_UNBAN.format(
                    msg['data']['moder_name'],
                    msg['data']['user_name']), category='chat')

    def _process_channel_counters(self):
        try:
            self.main_thread.viewers = self.main_thread.get_viewers()
        except Exception as exc:
            log.exception(exc)

    def _post_process_multiple_channels(self, message):
        if self.chat_module.conf_params()['config']['config']['show_channel_names']:
            message.channel_name = self.main_thread.nick

    def _send_message(self, comp):
        self._post_process_multiple_channels(comp)
        self.message_queue.put(comp)


class GGChat(WebSocketClient):
    def __init__(self, ws, **kwargs):
        super(self.__class__, self).__init__(ws, heartbeat_freq=kwargs.get('heartbeat_freq'),
                                             protocols=kwargs.get('protocols'))
        # Received value setting.
        self.ch_id = kwargs.get('ch_id')
        self.queue = kwargs.get('queue')
        self.gg_queue = Queue.Queue()

        self.main_thread = kwargs.get('main_thread')  # type: GGChannel
        self.chat_module = kwargs.get('chat_module')
        self.crit_error = False

        self.message_handler = GoodgameMessageHandler(self, gg_queue=self.gg_queue, **kwargs)
        self.message_handler.start()

    def opened(self):
        success_msg = "Connection Successful"
        log.info(success_msg)
        self.main_thread.status = CHANNEL_ONLINE
        try:
            self.main_thread.viewers = self.main_thread.get_viewers()
        except Exception as exc:
            log.exception(exc)
        self.system_message(CONNECTION_SUCCESS.format(self.main_thread.nick), category='connection')
        # Sending join channel command to goodgame websocket
        join = json.dumps({'type': "join", 'data': {'channel_id': self.ch_id, 'hidden': "true"}}, sort_keys=False)
        self.send(join)
        # self.ggPing()
        log.info("Sent join message")

    def closed(self, code, reason=None):
        """
        Codes used by LC
        4000 - Normal disconnect by LC
        4001 - Invalid Channel ID

        :param code: 
        :param reason: 
        """
        log.info("Connection Closed Down")
        self.main_thread.status = CHANNEL_OFFLINE
        if code in [4000, 4001]:
            self.crit_error = True
            self.system_message(CONNECTION_CLOSED.format(self.main_thread.nick),
                                category='connection')
        else:
            self.system_message(CONNECTION_DIED.format(self.main_thread.nick),
                                category='connection')
            timer = threading.Timer(5.0, self.main_thread.connect)
            timer.start()

    def received_message(self, mes):
        # Deserialize message to json for easier parsing
        self.gg_queue.put(json.loads(str(mes)))

    def system_message(self, msg, category='system'):
        self.queue.put(GoodgameSystemMessage(msg, category=category, channel_name=self.main_thread.nick))


class GGChannel(threading.Thread, Channel):
    def __init__(self, queue, address, nick, use_chid, **kwargs):
        threading.Thread.__init__(self)
        Channel.__init__(self)

        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = True
        self.queue = queue
        self.address = str(address)
        self.nick = nick

        self.chat_module = kwargs.get('chat_module')
        try:
            self.ch_id = int(nick)
        except:
            self.ch_id = None
        self.kwargs = kwargs
        self.ws = None

        self.smiles = {}

    def load_config(self):
        try:
            requests.get(API.format(''), timeout=5)
        except Exception as exc:
            log.error('API is not working')
            return False

        try:
            if self.ch_id:
                request = requests.get(API.format('streams/{}').format(self.ch_id))
                if request.status_code == 200:
                    channel_name = request.json()['channel']['key']
                    if self.nick != channel_name:
                        self.nick = channel_name
            else:
                request = requests.get(API.format('streams/{}').format(self.nick))
                if request.status_code == 200:
                    self.ch_id = request.json()['channel']['id']
        except Exception as exc:
            log.warning("Unable to get channel name, error {0}\nArgs: {1}".format(exc.message, exc.args))

        try:
            smile_request = requests.get(SMILE_API)
            if not smile_request.ok:
                raise IndexError('URL Error {}'.format(smile_request.reason))

            req_json = smile_request.json()
            for smile in req_json:
                self.smiles[smile['key']] = smile
        except Exception as exc:
            log.error("Unable to download smiles, error {0}\nArgs: {1}".format(exc.message, exc.args))

        return True

    def get_viewers(self):
        if not self.chat_module.conf_params()['config']['config']['check_viewers']:
            return NA_MESSAGE
        streams_url = API.format('streams/{0}'.format(self.nick))
        try:
            request = requests.get(streams_url)
            if request.ok:
                json_data = request.json()
                if json_data['status'] == 'Live':
                    return request.json().get('player_viewers')
                else:
                    return NA_MESSAGE
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get user count, error {0}\nArgs: {1}".format(exc.message, exc.args))

    def run(self):
        self.connect()

    def connect(self):
        try_count = 0
        while True:
            try_count += 1
            log.info("Connecting, try {0}".format(try_count))

            self._status = CHANNEL_PENDING
            if self.load_config():
                # Connecting to goodgame websocket
                self.ws = GGChat(self.address, protocols=['websocket'], queue=self.queue,
                                 ch_id=self.ch_id, nick=self.nick, smiles=self.smiles,
                                 heartbeat_freq=30, main_thread=self, **self.kwargs)
                try:
                    self.ws.connect()
                    self.ws.run_forever()
                    log.debug("Connection closed")
                    break
                except Exception as exc:
                    log.exception(exc)
            time.sleep(5)

    def stop(self):
        self.ws.close(4000)


def gg_message(nickname, text):
    return {
        'type': u'message',
        'data': {
            u'color': u'streamer',
            u'hideIcon': 0,
            u'mobile': 0,
            u'text': u'{}'.format(text),
            u'user_name': u'{}'.format(nickname),
            u'icon': u'none',
            u'message_id': ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        }
    }


class TestGG(threading.Thread):
    def __init__(self, main_class):
        super(TestGG, self).__init__()
        self.main_class = main_class  # type: GoodGame
        self.main_class.rest_add('POST', 'push_message', self.send_message)
        self.gg_handler = None

    def run(self):
        while True:
            try:
                thread = self.main_class.channels.items()[0][1]
                if thread.ws:
                    self.gg_handler = thread.ws.message_handler
                    break
            except:
                continue
        log.info("GG Testing mode online")

    def send_message(self, *args, **kwargs):
        nickname = kwargs.get('nickname', 'super_tester')
        text = kwargs.get('text', 'Kappa 123')

        self.gg_handler.process_message(gg_message(nickname, text))


class GoodGame(ChatModule):
    def __init__(self, *args, **kwargs):
        log.info("Initializing goodgame chat")
        ChatModule.__init__(self, *args, **kwargs)

        self.host = CONF_DICT['config']['socket']

    def load_module(self, *args, **kwargs):
        ChatModule.load_module(self, *args, **kwargs)
        if 'webchat' in self._loaded_modules:
            self._loaded_modules['webchat']['class'].add_depend('goodgame')
        self._conf_params['settings']['remove_text'] = self.get_remove_text()

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self):
        return CONF_GUI

    def _test_class(self):
        return TestGG(self)

    def _add_channel(self, chat):
        gg = GGChannel(self.queue, self.host, chat,
                       self._conf_params['config']['config']['use_channel_id'],
                       settings=self._conf_params['settings'], chat_module=self)
        self.channels[chat] = gg
        gg.start()

    def apply_settings(self, **kwargs):
        if 'webchat' in kwargs.get('from_depend', []):
            self._conf_params['settings']['remove_text'] = self.get_remove_text()
        ChatModule.apply_settings(self, **kwargs)
