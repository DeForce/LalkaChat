# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import json
import random
import threading
import os
import requests
import Queue
import logging

import time

from modules.helper.message import TextMessage, SystemMessage, RemoveMessageByUsers, RemoveMessageByIDs
from modules.helper.module import ChatModule, Channel
from ws4py.client.threadedclient import WebSocketClient

from modules.helper.system import NO_VIEWERS, translate_key
from modules.interface.types import LCStaticBox, LCBool, LCPanel

logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('beampro')
SOURCE = 'bp'
SOURCE_ICON = 'https://beam.pro/_latest/assets/favicons/favicon-32x32.png'
FILE_ICON = os.path.join('img', 'beampro.png')
SYSTEM_USER = 'Beam.pro'
ID_PREFIX = 'bp_{0}'

API_URL = 'https://beam.pro/api/v1{}'

CONF_DICT = LCPanel(icon=FILE_ICON)
CONF_DICT['config'] = LCStaticBox()
CONF_DICT['config']['show_pm'] = LCBool(True)

CONF_GUI = {
    'config': {
        'channels_list': {
            'view': 'list',
            'addable': 'true'
        }
    }
}


class BeamProAPIException(Exception):
    pass


class BeamProTextMessage(TextMessage):
    def __init__(self, user, text, mid):
        TextMessage.__init__(self, platform_id=SOURCE, icon=SOURCE_ICON,
                             user=user, text=text, mid=mid)


class BeamProSystemMessage(SystemMessage):
    def __init__(self, text, category='system', **kwargs):
        SystemMessage.__init__(self, text, platform_id=SOURCE, icon=SOURCE_ICON,
                               user=SYSTEM_USER, category=category, **kwargs)


class BeamProMessageHandler(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)

        self.queue = kwargs.get('queue')
        self.message_queue = kwargs.get('message_queue')
        self.channel_nick = kwargs.get('channel_nick')
        self.main_class = kwargs.get('main_class')  # type: beampro

    def run(self):
        while True:
            self.process_message(self.queue.get())

    def process_message(self, message):
        if 'event' in message['type']:
            self._process_event(message)

    def _process_event(self, message):
        event = message['event']
        if event == 'WelcomeEvent':
            self.main_class.set_channel_online(self.channel_nick)
        elif event == 'ChatMessage':
            self._process_chat_message(message)
        elif event == 'DeleteMessage':
            self._process_delete_event(message)
        elif event == 'PurgeMessage':
            self._process_purge_event(message)

    def _process_chat_message(self, message):
        log.debug(message)

        msg = BeamProTextMessage(
            message['data']['user_name'],
            self._get_text_message(message),
            ID_PREFIX.format(message['data']['id'])
        )
        self._send_message(msg)

    @staticmethod
    def _get_text_message(message):
        message_args = message['data']['message']['message']
        return ''.join([msg['text'] for msg in message_args])

    def _process_delete_event(self, message, text=None):
        if self.main_class.conf_params()['config']['config']['show_channel_names']:
            text = self.main_class.conf_params()['settings'].get('remove_text')
        id_to_delete = ID_PREFIX.format(message['data']['id'])
        self.message_queue.put(
            RemoveMessageByIDs(
                id_to_delete,
                text=text,
                platform=SOURCE
            )
        )

    def _process_purge_event(self, message, text=None):
        if self.main_class.conf_params()['config']['config']['show_channel_names']:
            text = self.main_class.conf_params()['settings'].get('remove_text')
        user_id = message['data']['user_id']
        nickname_req = requests.get(API_URL.format('/channels/{}'.format(user_id)))
        if not nickname_req.ok:
            raise BeamProAPIException("Unable to get user nickname")
        nickname = nickname_req.json()
        self._send_message(
            RemoveMessageByUsers(
                nickname,
                text=text,
                platform=SOURCE
            )
        )

    def _post_process_multiple_channels(self, message):
        if self.main_class.conf_params()['config']['config']['show_channel_names']:
            message.channel_name = self.channel_nick

    def _send_message(self, message):
        self._post_process_multiple_channels(message)
        self.message_queue.put(message)


class BeamProClient(WebSocketClient):
    def __init__(self, url, **kwargs):
        WebSocketClient.__init__(self, url, protocols=['chat'], heartbeat_freq=30)
        self.exited = False

        self.channel_id = kwargs.get('channel_id')
        self.channel_nick = kwargs.get('channel_nick')
        self.main_class = kwargs.get('main_class')  # type: beampro
        self.id = 0

        self.ws_queue = Queue.Queue()
        self.message_handler = BeamProMessageHandler(
            queue=self.ws_queue,
            message_queue=self.main_class.queue,
            channel_nick=self.channel_nick,
            main_class=self.main_class
        )
        self.message_handler.start()

        self._ping_th = threading.Thread(target=self.viewers_thread, name='BeamProAPIThread')
        self._ping_th.daemon = True
        self._ping_th.start()

    def opened(self):
        log.info("Connection Successful")
        payload = {
            "type": "method",
            "method": "auth",
            "arguments": [self.channel_id]
        }
        self.send_payload(payload)
        self.system_message(
            translate_key('beampro.connection_success').format(self.channel_nick)
        )

    def closed(self, code, reason=None):
        """
        Codes used by LC
        4000 - Normal disconnect by LC

        :param code: 
        :param reason: 
        """
        log.debug("%s %s", code, reason)
        log.info("Connection closed")
        if code in [4000]:
            self.system_message(
                translate_key('beampro.connection_closed').format(self.channel_nick)
            )
            self.exited = True
        else:
            self.system_message(
                translate_key('beampro.connection_died').format(self.channel_nick)
            )
        self.main_class.set_channel_offline(self.channel_nick)

    def received_message(self, message):
        self.ws_queue.put(json.loads(message.data))

    def system_message(self, msg, category='system'):
        self.main_class.queue.put(
            BeamProSystemMessage(
                msg, category, channel_name=self.channel_nick
            )
        )

    def send_payload(self, payload):
        payload['id'] = self.id
        self.id += 1
        self.send(json.dumps(payload))

    def viewers_thread(self):
        while True:
            self.main_class.set_viewers(
                self.channel_nick,
                self.main_class.get_viewers(self.channel_id)
            )
            time.sleep(10)


class BeamProChannel(threading.Thread, Channel):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        Channel.__init__(self)

        self.daemon = True

        self.queue = kwargs.get('queue')
        self.channel = kwargs.get('channel')
        self.settings = kwargs.get('settings')
        self.main_class = kwargs.get('chat_module')
        self.ws = None

        self.channel_id = None
        self.channel_nick = None
        self.endpoints = None

    def run(self):
        try_count = 0
        while True:
            try_count += 1
            log.info("Connecting, try {0}".format(try_count))
            self.get_connection_info()
            self.ws = BeamProClient(
                random.choice(self.endpoints),
                channel_id=self.channel_id,
                channel_nick=self.channel_nick,
                main_class=self.main_class
            )
            self.ws.connect()
            self.ws.run_forever()
            if self.ws.exited:
                break
            time.sleep(5)

    def get_connection_info(self):
        channel_id_req = requests.get(API_URL.format('/channels/{}'.format(self.channel)))
        if not channel_id_req.ok:
            raise BeamProAPIException("Unable to get channel information")
        channel_data = channel_id_req.json()
        csrf_token = channel_id_req.headers['x-csrf-token']
        self.channel_id = channel_data['id']
        self.channel_nick = channel_data['token']

        chat_info_req = requests.get(API_URL.format('/chats/{}'.format(self.channel_id)), headers={
            'X-CSRF-Token': csrf_token
        })
        if not chat_info_req.ok:
            raise BeamProAPIException("Unable to get chat endpoint information")
        chat_info = chat_info_req.json()
        self.endpoints = chat_info['endpoints']

    def stop(self):
        self.ws.close(4000)


class TestBeamProMessage(object):
    def __init__(self, nickname, text):
        self.data = {
            u'data': {
                u'message': {
                    u'message': [{
                        u'text': '{}'.format(text)
                    }],
                },
                u'user_name': '{}'.format(nickname),
                u'id': u'7a7a8fa0-1640-11e7-b968-c71b13ffd484',
            },
            u'type': u'event',
            u'event': u'ChatMessage'
        }


class TestBeamPro(threading.Thread):
    def __init__(self, main_class):
        super(TestBeamPro, self).__init__()
        self.main_class = main_class  # type: beampro
        self.main_class.rest_add('POST', 'push_message', self.send_message)
        self.beampro = None

    def run(self):
        while True:
            try:
                thread = self.main_class.channels.items()[0][1]
                if thread.ws:
                    self.beampro = thread.ws.message_handler
                    break
            except:
                continue
        log.info("BeamPro Testing mode online")

    def send_message(self, *args, **kwargs):
        nickname = kwargs.get('nickname', 'super_tester')
        text = kwargs.get('text', 'Kappa 123')

        self.beampro.process_message(TestBeamProMessage(nickname, text).data)


class beampro(ChatModule):
    def __init__(self, *args, **kwargs):
        log.info("Initializing beampro chat")
        ChatModule.__init__(self, *args, **kwargs)

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self, *args, **kwargs):
        return CONF_GUI

    def _test_class(self):
        return TestBeamPro(self)

    def load_module(self, *args, **kwargs):
        ChatModule.load_module(self, *args, **kwargs)
        if 'webchat' in self._loaded_modules:
            self._loaded_modules['webchat']['class'].add_depend('beampro')
        self._conf_params['settings']['remove_text'] = self.get_remove_text()

    @staticmethod
    def get_viewers(channel_id):
        viewers_req = requests.get(API_URL.format('/chats/{}/users'.format(channel_id)))
        if not viewers_req.ok:
            return NO_VIEWERS
        return viewers_req.headers['x-total-count']

    def _add_channel(self, chat):
        ChatModule._add_channel(self, chat)
        self.channels[chat] = BeamProChannel(
            queue=self.queue,
            channel=chat,
            settings=self._conf_params['settings'],
            chat_module=self)
        self.channels[chat].start()

    def apply_settings(self, **kwargs):
        if 'webchat' in kwargs.get('from_depend', []):
            self._conf_params['settings']['remove_text'] = self.get_remove_text()
        ChatModule.apply_settings(self, **kwargs)
