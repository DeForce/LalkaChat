# Copyright (C) 2016   CzT/Vladislav Ivanov
import Queue
import json
import random
import re
import threading
import os
import logging
from collections import OrderedDict
import time

import requests
from ws4py.client.threadedclient import WebSocketClient

from modules.helper.message import TextMessage, Emote, SystemMessage, RemoveMessageByUser
from modules.helper.module import ChatModule
from modules.helper.system import translate_key, EMOTE_FORMAT
from modules.interface.types import LCStaticBox, LCBool, LCPanel

logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('hitbox')
SOURCE = 'hb'
SOURCE_ICON = 'http://www.hitbox.tv/favicon.ico'
FILE_ICON = os.path.join('img', 'hitboxtv.png')
SYSTEM_USER = 'Hitbox.tv'
ID_PREFIX = 'hb_{}'
SMILE_REGEXP = r'(^|\s)({})(?=(\s|$))'
SMILE_FORMAT = r'\1:{}:\3'

API_URL = 'https://api.hitbox.tv{}'
CDN_URL = 'http://edge.sf.hitbox.tv{}'

PING_DELAY = 10

CONF_DICT = LCPanel(icon=FILE_ICON)
CONF_DICT['config'] = LCStaticBox()
CONF_DICT['config']['show_nickname_colors'] = LCBool(False)

CONF_GUI = {
    'config': {
        'channels_list': {
            'view': 'list',
            'addable': 'true'
        },
    }
}


class HitboxAPIError(Exception):
    pass


class HitboxTextMessage(TextMessage):
    def __init__(self, user, text, mid, nick_colour):
        TextMessage.__init__(self, platform_id=SOURCE, icon=SOURCE_ICON,
                             user=user, text=text, mid=mid, nick_colour=nick_colour)


class HitboxSystemMessage(SystemMessage):
    def __init__(self, text, category='system'):
        SystemMessage.__init__(self, platform_id=SOURCE, icon=SOURCE_ICON,
                               user=SYSTEM_USER, text=text, category=category)


class HitboxMessageHandler(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)

        self.queue = kwargs.get('queue')
        self.message_queue = kwargs.get('message_queue')
        self.channel = kwargs.get('channel')
        self.main_class = kwargs.get('main_class')  # type: hitbox
        self.smiles = kwargs.get('smiles')

    def run(self):
        while True:
            self.process_message(self.queue.get())

    def process_message(self, message):
        for msg in message['args']:
            self._process_message(json.loads(msg))

    def _process_message(self, message):
        method = message['method']
        if method == 'loginMsg':
            self.main_class.set_channel_online(self.channel)
        elif method == 'serverMsg':
            self._process_trash_msg(message['params'])
        elif method == 'pollMsg':
            self._process_trash_msg(message['params'])
        elif method == 'motdMsg':
            self._process_trash_msg(message['params'])
        elif method == 'chatMsg':
            self._process_chat_msg(message['params'])
        elif method == 'infoMsg':
            self._process_info_msg(message['params'])
        elif method == 'userList':
            self._process_user_list(message['params'])
        else:
            log.debug(message)

    def _process_user_list(self, message):
        viewers = []
        for item, data in message['data'].items():
            if item == 'Guests':
                continue
            else:
                viewers += data

        viewers = len(set(viewers))
        viewers += message['data']['Guests'] if message['data']['Guests'] else 0
        self.main_class.set_viewers(self.channel, viewers)

    def _process_chat_msg(self, message):
        msg = HitboxTextMessage(
            user=message['name'],
            text=message['text'],
            mid=ID_PREFIX.format(message['id']),
            nick_colour='#{}'.format(message['nameColor']) if self._show_color() else None,
        )

        self._send_message(msg)

    def _process_info_msg(self, message):
        user_to_delete = message['variables']['user']
        self.message_queue.put(
            RemoveMessageByUser(
                user_to_delete,
                text=self.main_class.conf_params()['settings'].get('remove_text')
            )
        )

    def _show_color(self):
        return self.main_class.conf_params()['config']['config']['show_nickname_colors']

    def _post_process_emotes(self, message):
        for word in message.text.split():
            if word in self.smiles:
                message.text = re.sub(SMILE_REGEXP.format(re.escape(word)),
                                      r'\1{}\3'.format(EMOTE_FORMAT.format(word)),
                                      message.text)
                message.emotes.append(Emote(word, CDN_URL.format(self.smiles[word])))

    def _post_process_multiple_channels(self, message):
        if self.main_class.conf_params()['config']['config']['show_channel_names']:
            message.channel_name = self.channel

    def _send_message(self, message):
        self._post_process_emotes(message)
        self.message_queue.put(message)

    def _process_trash_msg(self, message):
        pass


class HitboxViewersWS(WebSocketClient):
    def __init__(self, url, **kwargs):
        WebSocketClient.__init__(self, url, heartbeat_freq=30)

        self.main_class = kwargs.get('main_class')  # type: hitbox
        self.channel = kwargs.get('channel')

    def opened(self):
        self.send(json.dumps({
            'method': 'joinChannel',
            'params': {
                'channel': self.channel.lower(),
                'name': 'UnknownSoldier',
                'token': None,
                'hideBuffered': True
            }
        }))

    def closed(self, code, reason=None):
        log.info('Viewers Connection closed %s, %s', code, reason)

    def received_message(self, message):
        data = json.loads(message.data)
        method = data['method']
        if method == 'infoMsg':
            self.main_class.set_viewers(self.channel, data['params']['viewers'])


class HitboxClient(WebSocketClient):
    def __init__(self, url, **kwargs):
        ws_url = self.get_connection_url(url)

        WebSocketClient.__init__(self, ws_url)

        self.channel = kwargs.get('channel')
        self.main_class = kwargs.get('main_class')
        self.exited = False

        self.ws_queue = Queue.Queue()
        self.message_handler = HitboxMessageHandler(
            queue=self.ws_queue,
            message_queue=self.main_class.queue,
            channel=self.channel,
            main_class=self.main_class,
            smiles=kwargs.get('smiles')
        )
        self.message_handler.start()

        self._viewers_th = HitboxViewersWS(
            url='wss://{}/viewer'.format(random.choice(kwargs.get('viewerss'))),
            main_class=self.main_class,
            channel=self.channel
        )
        self._viewers_th.daemon = True

    def opened(self):
        log.info("Connection Successful")
        self.system_message(
            translate_key('hitbox.connection_success').format(self.channel)
        )
        self._join_channel()
        self._viewers_th.connect()

    def closed(self, code, reason=None):
        """
        Codes used by LC
        4000 - Normal disconnect by LC

        :param code: 
        :param reason: 
        """
        log.debug("%s %s", code, reason)
        log.info("Connection closed")
        self._viewers_th.close()
        if code in [4000]:
            self.system_message(
                translate_key('hitbox.connection_closed').format(self.channel)
            )
            self.exited = True
        else:
            self.system_message(
                translate_key('hitbox.connection_died').format(self.channel)
            )
        self.main_class.set_offline(self.channel)

    def received_message(self, message):
        if message.data == '2::':
            self._respond_ping()
        elif message.data.startswith('5::'):
            self.ws_queue.put(json.loads(message.data[4:]))

    def _respond_ping(self):
        self.send('2::')

    def _join_channel(self):
        login_command = {
            'name': 'message',
            'args': [
                {
                    'method': 'joinChannel',
                    'params': {
                        'channel': self.channel.lower(),
                        'name': 'UnknownSoldier',
                        'token': None,
                        'hideBuffered': True
                    }
                }
            ]
        }
        self.send_message(5, login_command)

    def send_message(self, msg_type, data):
        message = "{}:::{}".format(msg_type, json.dumps(data))
        self.send(message)

    @staticmethod
    def get_connection_url(url):
        user_id_req = requests.get('https://{}/socket.io/1/'.format(url))
        if not user_id_req.ok:
            raise HitboxAPIError("Unable to get userid")
        user_id = user_id_req.text.split(':')[0]
        return 'wss://{}/socket.io/1/websocket/{}'.format(url, user_id)

    def system_message(self, msg, category='system'):
        self.main_class.queue.put(
            HitboxSystemMessage(msg, category=category)
        )


class HitboxInitThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True

        self.queue = kwargs.get('queue')
        self.channel = kwargs.get('channel')
        self.settings = kwargs.get('settings')
        self.main_class = kwargs.get('chat_module')
        self.ws = None

        self.endpoints = []
        self.viewer_endpoints = []
        self.smiles = {}

    def run(self):
        try_count = 0
        while True:
            try_count += 1
            log.info("Connecting, try {0}".format(try_count))
            self.get_connection_info()
            self.ws = HitboxClient(
                random.choice(self.endpoints),
                viewerss=self.viewer_endpoints,
                channel=self.channel,
                main_class=self.main_class,
                smiles=self.smiles
            )
            self.ws.connect()
            self.ws.run_forever()
            if self.ws.exited:
                break
            time.sleep(5)

    def get_connection_info(self):
        servers_req = requests.get(API_URL.format('/chat/servers'))
        if not servers_req.ok:
            raise HitboxAPIError("Unable to get server list")
        self.endpoints = [item['server_ip'] for item in servers_req.json()]

        smiles_req = requests.get(API_URL.format('/chat/icons/{}'.format(self.channel)))
        if not smiles_req.ok:
            raise HitboxAPIError("Unable to get smiles")
        self.smiles = {}
        for smile in smiles_req.json()['items']:
            self.smiles[smile['icon_short']] = smile['icon_path']
            self.smiles[smile['icon_short_alt']] = smile['icon_path']

        viewers_req = requests.get(API_URL.format('/player/server'))
        if not servers_req.ok:
            raise HitboxAPIError("Unable to get viewer server settings")
        viewers = viewers_req.json()
        self.viewer_endpoints = [server['server_ip'] for server in viewers]

    def stop(self):
        self.ws.close(4000)


class HitboxMessage(object):
    def __init__(self, nickname, text):
        self.data = {
            u'args': [json.dumps({
                u'params': {
                    u'name': nickname,
                    u'id': ID_PREFIX.format(random.randint(1, 50)),
                    u'text': text,
                    u'nameColor': '000000'
                },
                u'method': u'chatMsg'
            })]
        }


class TestHitbox(threading.Thread):
    def __init__(self, main_class, **kwargs):
        super(TestHitbox, self).__init__()
        self.main_class = main_class  # type: hitbox
        self.main_class.rest_add('POST', 'push_message', self.send_message)
        self.chat = None

    def run(self):
        while True:
            try:
                thread = self.main_class.channels.items()[0][1]
                if thread.ws:
                    self.chat = thread.ws.message_handler
                    break
            except:
                continue
        log.info("Hitbox Testing mode online")

    def send_message(self, *args, **kwargs):
        nickname = kwargs.get('nickname', 'super_tester')
        text = kwargs.get('text', 'Kappa 123')

        self.chat.process_message(HitboxMessage(nickname, text).data)


class hitbox(ChatModule):
    def __init__(self, *args, **kwargs):
        log.info("Initializing hitbox chat")
        ChatModule.__init__(self, *args, **kwargs)

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self, *args, **kwargs):
        return CONF_GUI

    def _test_class(self):
        return TestHitbox(self)

    def _add_channel(self, chat):
        ChatModule._add_channel(self, chat)
        self.channels[chat] = HitboxInitThread(
            queue=self.queue,
            channel=chat,
            settings=self._conf_params['settings'],
            chat_module=self)
        self.channels[chat].start()

    def get_viewers(self, ws, channel):
        request = {
            "name": "message",
            "args": [
                {
                    "method": "getChannelUserList",
                    "params": {
                        "channel": channel
                    }
                }
            ]
        }
        ws.send_message(5, request)
