# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import queue
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
from modules.helper.message import TextMessage, SystemMessage, RemoveMessageByIDs
from modules.helper.module import ChatModule, Channel, CHANNEL_ONLINE, CHANNEL_PENDING, CHANNEL_OFFLINE, \
    CHANNEL_DISABLED
from modules.helper.system import translate_key, EMOTE_FORMAT, NO_VIEWERS
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
CONF_DICT['config']['show_channel_names'] = LCBool(False)
CONF_DICT['config']['use_channel_id'] = LCBool(False)
CONF_DICT['config']['check_viewers'] = LCBool(True)
SMILE_REGEXP = r':(\w+|\d+):'
SMILE_FORMAT = ':{}:'

CONF_GUI = {
    'config': {
        'hidden': ['socket'],
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
                if not smile_info['premium']:
                    if smile_info['donat'] == 0:
                        allow = True
                    elif smile_info['donat'] <= int(payments):
                        allow = True
                else:
                    if premium:
                        allow = True

            for premium_item in prems:
                if smile_info['channel_id'] == premium_item:
                    if smile_info['premium']:
                        allow = True
                        gif = True

            if allow:
                self._text = self._text.replace(SMILE_FORMAT.format(smile), EMOTE_FORMAT.format(smile))
                url = smile_info['images']['big']
                if gif and smile_info['images']['gif']:
                    url = smile_info['images']['gif']
                self.add_emote(smile, url)


class GoodgameMessageHandler(threading.Thread):
    def __init__(self, ws_class, gg_queue=None, nick=None, smiles=None, channel_class=None, chat_module=None, **kwargs):
        super(self.__class__, self).__init__()
        self.ws_class = ws_class
        self.daemon = True
        self.gg_queue = gg_queue

        self.nick = nick
        self.smiles = smiles
        self.channel_class = channel_class
        self.chat_module = chat_module
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

        if re.match(f'^{self.nick},'.lower(), message.text.lower()):
            if self.chat_module.get_config('config', 'show_pm'):
                message.pm = True
        self._send_message(message)

    def _process_join(self):
        self.channel_class.put_system_message(CHANNEL_JOIN_SUCCESS.format(self.nick))

    def _process_error(self, msg):
        log.info("Received error message: %s", msg)
        if msg['data']['errorMsg'] == 'Invalid channel id':
            self.ws_class.close(reason='INV_CH_ID')
            log.error("Failed to find channel on GoodGame, please check channel name")

    def _process_user_warn(self, msg):
        self.channel_class.put_system_message(MESSAGE_WARNING.format(
            msg['data']['moder_name'], msg['data']['user_name']))

    def _process_remove_message(self, msg):
        remove_id = ID_PREFIX.format(msg['data']['message_id'])
        self.channel_class.put_message(RemoveMessageByIDs(remove_id, platform=SOURCE))

    def _process_user_ban(self, msg):
        if msg['data']['duration']:
            self.channel_class.put_system_message(MESSAGE_BAN.format(
                msg['data']['moder_name'],
                msg['data']['user_name'],
                msg['data']['duration']/60,
                msg['data']['reason']))
        else:
            if msg['data']['permanent']:
                self.channel_class.put_system_message(
                    MESSAGE_BAN_PERM.format(msg['data']['moder_name'], msg['data']['user_name']))
            else:
                self.channel_class.put_system_message(MESSAGE_UNBAN.format(
                    msg['data']['moder_name'],
                    msg['data']['user_name']))

    def _process_channel_counters(self):
        try:
            self.channel_class.viewers = self.channel_class.get_viewers()
        except Exception as exc:
            log.exception(exc)

    def _post_process_multiple_channels(self, message):
        if self.chat_module.get_config('config', 'show_channel_names'):
            message.channel_name = self.channel_class.nick

    def _send_message(self, message):
        self._post_process_multiple_channels(message)
        self.channel_class.put_message(message)


class GGChat(WebSocketClient):
    def __init__(self, ws, ch_id=None, channel_class=None, chat_module=None, **kwargs):
        super(self.__class__, self).__init__(ws, heartbeat_freq=kwargs.get('heartbeat_freq'),
                                             protocols=kwargs.get('protocols'))
        # Received value setting.
        self.ch_id = ch_id
        self.gg_queue = queue.Queue()

        self.channel_class = channel_class
        self.chat_module = chat_module
        self.crit_error = False

        self.message_handler = GoodgameMessageHandler(
            self, gg_queue=self.gg_queue, channel_class=self.channel_class, chat_module=self.chat_module,
            **kwargs)
        self.message_handler.start()

    def opened(self):
        success_msg = "Connection Successful"
        log.info(success_msg)
        self.channel_class.status = CHANNEL_ONLINE
        try:
            self.channel_class.viewers = self.channel_class.get_viewers()
        except Exception as exc:
            log.exception(exc)
        self.channel_class.put_system_message(CONNECTION_SUCCESS.format(self.channel_class.nick))
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
        self.channel_class.status = CHANNEL_OFFLINE
        if code in [4000, 4001]:
            self.crit_error = True
            self.channel_class.put_system_message(CONNECTION_CLOSED.format(self.channel_class.nick))
        else:
            self.channel_class.put_system_message(CONNECTION_DIED.format(self.channel_class.nick))
            timer = threading.Timer(5.0, self.channel_class.connect)
            timer.start()

    def received_message(self, mes):
        # Deserialize message to json for easier parsing
        self.gg_queue.put(json.loads(str(mes)))


class GGChannel(threading.Thread, Channel):
    def __init__(self, queue, address, nick, use_chid, chat_module=None, **kwargs):
        threading.Thread.__init__(self)
        Channel.__init__(self, nick, queue, icon=SOURCE_ICON, platform_id=SOURCE, system_user=SYSTEM_USER)

        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = True
        self.address = str(address)
        self.nick = nick

        self.chat_module = chat_module
        try:
            self.ch_id = int(nick)
        except:
            self.ch_id = None
        self.kwargs = kwargs
        self.ws = None

        self.smiles = {}

    def load_config(self):
        try:
            if self.ch_id:
                request = requests.get(API.format(f'streams/{self.ch_id}'))
                if request.status_code == 200:
                    channel_name = request.json()['channel']['key']
                    if self.nick != channel_name:
                        self.nick = channel_name
            else:
                request = requests.get(API.format(f'streams/{self.nick}'))
                if request.status_code == 200:
                    self.ch_id = request.json()['channel']['id']
        except Exception as exc:
            log.warning("Unable to get channel name, error %s\nArgs: %s", exc, exc.args)

        try:
            smile_request = requests.get(SMILE_API)
            if not smile_request.ok:
                raise IndexError(f'URL Error {smile_request.reason}')

            req_json = smile_request.json()
            for smile in req_json:
                self.smiles[smile['key']] = smile
        except Exception as exc:
            log.error("Unable to download smiles, error %s\nArgs: %s", exc, exc.args)

        return True

    def get_viewers(self):
        if not self.chat_module.get_config('config', 'check_viewers'):
            return NO_VIEWERS
        streams_url = API.format(f'streams/{self.nick}')
        try:
            request = requests.get(streams_url)
            if request.ok:
                json_data = request.json()
                if json_data['status'] == 'Live':
                    return request.json().get('player_viewers')
                else:
                    return NO_VIEWERS
            else:
                raise Exception(f"Not successful status code: {request.status_code}")
        except Exception as exc:
            log.warning("Unable to get user count, error %s\nArgs: %s", exc, exc.args)

    def run(self):
        self.connect()

    def connect(self):
        try_count = 0
        while True:
            try_count += 1

            if self._status == CHANNEL_DISABLED:
                break

            log.info("Connecting, try %s", try_count)
            self._status = CHANNEL_PENDING
            if self.load_config():
                # Connecting to goodgame websocket
                self.ws = GGChat(self.address, protocols=['websocket'], queue=self.queue,
                                 ch_id=self.ch_id, nick=self.nick, smiles=self.smiles,
                                 heartbeat_freq=30, channel_class=self, chat_module=self.chat_module,
                                 **self.kwargs)
                try:
                    self.ws.connect()
                    self.ws.run_forever()
                    log.debug("Connection closed")
                    break
                except Exception as exc:
                    log.exception(exc)
            time.sleep(5)

    def stop(self):
        self._status = CHANNEL_DISABLED
        self.ws.close(4000)


def gg_message(nickname, text):
    return {
        'type': 'message',
        'data': {
            'color': 'streamer',
            'hideIcon': 0,
            'mobile': 0,
            'text': f'{text}',
            'user_name': f'{nickname}',
            'icon': 'none',
            'message_id': ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        }
    }


class GoodGame(ChatModule):
    def __init__(self, *args, **kwargs):
        log.info("Initializing goodgame chat")
        ChatModule.__init__(self, config=CONF_DICT, gui=CONF_GUI, *args, **kwargs)

        self.host = CONF_DICT['config']['socket']

    def load_module(self, *args, **kwargs):
        ChatModule.load_module(self, *args, **kwargs)

    def _add_channel(self, chat):
        gg = GGChannel(self.queue, self.host, chat,
                       self.get_config('config', 'use_channel_id'),
                       settings=self._conf_params['settings'], chat_module=self)
        self.channels[chat] = gg
        gg.start()
