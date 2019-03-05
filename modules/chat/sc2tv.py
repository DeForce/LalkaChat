# Copyright (C) 2016   CzT/Vladislav Ivanov
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
from modules.helper.message import TextMessage, SystemMessage, Emote
from modules.helper.module import ChatModule, Channel, CHANNEL_ONLINE, CHANNEL_NO_VIEWERS, CHANNEL_OFFLINE, \
    CHANNEL_DISABLED
from modules.helper.system import translate_key, EMOTE_FORMAT
from modules.interface.types import LCStaticBox, LCPanel, LCBool, LCText

logging.getLogger('requests').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
log = logging.getLogger('sc2tv')
SOURCE = 'fs'
SOURCE_ICON = 'https://peka2.tv/favicon-32x32.png'
FILE_ICON = os.path.join('img', 'fs.png')
SYSTEM_USER = 'Peka2.tv'
SMILE_REGEXP = r':(\w+|\d+):'
SMILE_FORMAT = ':{}:'
API_URL = 'https://peka2.tv/api{}'

PING_DELAY = 25

CONF_DICT = LCPanel(icon=FILE_ICON)
CONF_DICT['config'] = LCStaticBox()
CONF_DICT['config']['show_pm'] = LCBool(True)
CONF_DICT['config']['socket'] = LCText('wss://chat.peka2.tv/')
CONF_DICT['config']['show_channel_names'] = LCBool(False)

CONF_GUI = {
    'config': {
        'hidden': ['socket'],
        'channels_list': {
            'view': 'list',
            'addable': 'true'
        },
    },
    'non_dynamic': ['config.socket'],
}

CONNECTION_SUCCESS = translate_key(MODULE_KEY.join(['sc2tv', 'connection_success']))
CONNECTION_DIED = translate_key(MODULE_KEY.join(['sc2tv', 'connection_died']))
CONNECTION_CLOSED = translate_key(MODULE_KEY.join(['sc2tv', 'connection_closed']))
CONNECTION_JOINING = translate_key(MODULE_KEY.join(['sc2tv', 'joining']))
CHANNEL_JOIN_SUCCESS = translate_key(MODULE_KEY.join(['sc2tv', 'join_success']))


class Peka2TVAPIError(Exception):
    pass


def allow_smile(smile, subscriptions, allow=False):
    if smile['user']:
        channel_id = smile['user']['id']
        for sub in subscriptions:
            if sub == channel_id:
                allow = True
    else:
        allow = True
    return allow


class FsChatMessage(TextMessage):
    def __init__(self, user, text, subscr):
        self._user = user
        self._text = text
        self._subscriptions = subscr

        TextMessage.__init__(self, platform_id=SOURCE, icon=SOURCE_ICON,
                             user=self.user, text=self.text)

    def process_smiles(self, smiles):
        smiles_array = re.findall(SMILE_REGEXP, self._text)
        for smile in smiles_array:
            for smile_find in smiles:
                if smile_find['code'] == smile.lower():
                    if allow_smile(smile_find, self._subscriptions):
                        self._text = self._text.replace(SMILE_FORMAT.format(smile),
                                                        EMOTE_FORMAT.format(smile))
                        self._emotes.append(Emote(smile, smile_find['url']))

    def process_pm(self, to_name, channel_name, show_pm):
        self._text = f'@{to_name},{self.text}'
        if to_name == channel_name:
            if show_pm:
                self._pm = True


class FsSystemMessage(SystemMessage):
    def __init__(self, text, category='system', **kwargs):
        SystemMessage.__init__(self, text, platform_id=SOURCE, icon=SOURCE_ICON,
                               user=SYSTEM_USER, category=category, **kwargs)


class FsChat(WebSocketClient):
    def __init__(self, ws, queue, channel_name, **kwargs):
        super(self.__class__, self).__init__(ws, protocols=kwargs.get('protocols', None))
        # Received value setting.
        self.source = SOURCE
        self.queue = queue
        self.channel_name = channel_name

        self.main_thread = kwargs.get('main_thread')  # type: FsChannel
        self.chat_module = kwargs.get('chat_module')  # type: SC2TV
        self.crit_error = False

        self.channel_id = self.fs_get_id()

        self.smiles = kwargs.get('smiles')

        self.iter = 0
        self.duplicates = []
        self.users = []
        self.request_array = []
        self.bufferForDup = 20

    def opened(self):
        log.info("Websocket Connection Succesfull")
        self.fs_system_message(CONNECTION_SUCCESS, category='connection')

    def closed(self, code, reason=None):
        """
        Codes used by LC
        4000 - Normal disconnect by LC
        4001 - Invalid Channel ID

        :param code: 
        :param reason: 
        """
        self.main_thread.status = CHANNEL_OFFLINE
        if code in [4000, 4001]:
            self.crit_error = True
            self.fs_system_message(CONNECTION_CLOSED.format(self.channel_name),
                                   category='connection')
        else:
            log.info("Websocket Connection Closed Down with error %s, %s", code, reason)
            self.fs_system_message(
                CONNECTION_DIED.format(self.channel_name),
                category='connection')
            timer = threading.Timer(5.0, self.main_thread.connect)
            timer.start()

    def fs_system_message(self, message, category='system'):
        self.queue.put(FsSystemMessage(message, category=category, channel_name=self.channel_name))

    def received_message(self, mes):
        mes.data = mes.data.decode('utf-8')
        if mes.data == '40':
            return
        if mes.data in ['2', '3']:
            return
        log.debug('received message %s', mes)
        regex = re.match(r'(\d+)(.*)', mes.data)
        sio_iter, json_message = regex.groups()
        if sio_iter == '0':
            self._process_welcome()
        elif sio_iter[:2] in '42':
            self._process_websocket_event(json.loads(json_message))
        elif sio_iter[:2] in '43':
            self._process_websocket_ack(sio_iter[2:], json.loads(json_message))

    def fs_get_id(self):
        # We get ID from POST request to funstream API, and it hopefuly
        #  answers us the correct ID of the channel we need to connect to
        payload = {'name': self.channel_name}
        try:
            request = requests.post(API_URL.format("/user"), data=payload, timeout=5)
            if request.ok:
                channel_id = json.loads(re.findall('{.*}', request.text)[0])['id']
                return channel_id
            else:
                error_message = request.json()
                if 'message' in error_message:
                    log.error("Unable to get channel ID. %s", error_message['message'])
                    self.closed(4000, 'INV_CH_ID')
                else:
                    log.error("Unable to get channel ID. No message available")
                    self.closed(4000, 'INV_CH_ID')
        except:
            log.info("Unable to get information from api")
        return None

    def fs_join(self):
        # Then we send the message acording to needed format and
        #  hope it joins us
        logging.debug("Joining Channel %s", str(self.channel_id))
        if self.channel_id:
            payload = ['/chat/join', {'channel': f'stream/{self.channel_id}'}]
            self.fs_send(payload)

            msg_joining = CONNECTION_JOINING
            self.fs_system_message(msg_joining.format(self.channel_name), category='connection')
            log.debug(msg_joining.format(self.channel_id))

    def fs_send(self, payload):
        iter_sio = "42"+str(self.iter)

        self.send(f'{iter_sio}{json.dumps(payload)}')
        history_item = {
            'iter': str(self.iter),
            'payload': payload
        }
        self.iter += 1
        if len(self.request_array) > 20:
            del self.request_array[0]
        self.request_array.append(history_item)

    def fs_ping(self):
        ping_thread = FsPingThread(self)
        ping_thread.start()

    def _process_websocket_event(self, message):
        event_from, event_dict = message
        if event_from == '/chat/message':
            self._process_message(event_dict)

    def _process_websocket_ack(self, sio_id, message):
        if isinstance(message, list):
            if len(message) == 1:
                message = message[0]
        for item in self.request_array:  # type: dict
            if item['iter'] == sio_id:
                item_path = item['payload'][0]
                self._process_answer(item_path, message)
                break

    def _process_welcome(self):
        self.fs_join()
        self.fs_ping()

    def _process_answer(self, path, message):
        if path == '/chat/join':
            self._process_joined()
        elif path == '/chat/channel/list':
            self._process_channel_list(message)

    def _process_message(self, message):
        try:
            self.duplicates.index(message['id'])
        except ValueError:
            msg = FsChatMessage(message['from']['name'], message['text'], message['store']['subscriptions'])
            msg.process_smiles(self.smiles)
            if message['to']:
                msg.process_pm(message['to'].get('name'), self.channel_name,
                               self.chat_module.get_config('config', 'show_pm'))

            self.duplicates.append(message['id'])
            if len(self.duplicates) > self.bufferForDup:
                self.duplicates.pop(0)
            self._send_message(msg)

    def _process_joined(self):
        self.main_thread.status = CHANNEL_ONLINE
        self.fs_system_message(CHANNEL_JOIN_SUCCESS.format(self.channel_name), category='connection')

    def _process_channel_list(self, message):
        self.main_thread.viewers = message['result']['amount']

    def _post_process_multiple_channels(self, message):
        if self.chat_module.get_config('config', 'show_channel_names'):
            message.channel_name = self.channel_name

    def _send_message(self, comp):
        self._post_process_multiple_channels(comp)
        self.queue.put(comp)


class FsPingThread(threading.Thread):
    def __init__(self, ws):
        threading.Thread.__init__(self)
        self.daemon = "True"
        # Using main websocket
        self.ws = ws  # type: FsChat

    def run(self):
        while not self.ws.terminated:
            self.ws.main_thread.status = CHANNEL_ONLINE
            self.ws.send("2")
            self.ws.main_thread.get_viewers()
            time.sleep(PING_DELAY)


class FsChannel(threading.Thread, Channel):
    def __init__(self, queue, socket, channel_name, **kwargs):
        Channel.__init__(self, channel_name)
        threading.Thread.__init__(self)

        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = "True"
        self.queue = queue
        self.socket = str(socket)
        self.chat_module = kwargs.get('chat_module')
        self.smiles = []
        self.kwargs = kwargs

        self.slug = channel_name
        self.ws = None

    def run(self):
        self.connect()

    def connect(self):
        # Connecting to funstream websocket
        try_count = 0
        while True:
            if self._status == CHANNEL_DISABLED:
                break

            try:
                try_count += 1
                log.info("Connecting, try %s", try_count)
                self._get_info()
                self.ws = FsChat(self.socket, self.queue, self.get_channel_name(),
                                 protocols=['websocket'], smiles=self.smiles,
                                 main_thread=self, **self.kwargs)
                if self.ws.crit_error:
                    log.critical("Got critical error, halting")
                    break
                elif self.ws.channel_id and self.smiles:
                    self.ws.connect()
                    self.ws.run_forever()
                    break
                time.sleep(5)
            except Exception as exc:
                log.error('Exception occured %s', exc)

    def get_channel_name(self):
        user_payload = {'name': self.slug}
        user_req = requests.post(API_URL.format('/user'), timeout=5, data=user_payload)
        if not user_req.ok:
            user_payload = {'slug': self.slug}
            user_req = requests.post(API_URL.format('/user'), timeout=5, data=user_payload)
            if not user_req.ok:
                raise AttributeError('Unable to find user %s', self.slug)

        self.slug = user_req.json()['slug']
        channel_req = requests.post(API_URL.format('/stream'), timeout=5, data={'slug': user_req.json()['slug']})
        if channel_req.ok:
            r_json = channel_req.json()
            return r_json['owner']['name']

    def stop(self):
        self._status = CHANNEL_DISABLED
        self.ws.send("11")
        self.ws.close(4000, reason="CLOSE_OK")

    def get_viewers(self):
        status_data = {'slug': self.slug}
        request = ['/chat/channel/list', {'channel': f'stream/{self.ws.channel_id}'}]
        try:
            status_request = requests.post(API_URL.format('/stream'), timeout=10, data=status_data)
            if status_request.ok:
                if status_request.json()['online']:
                    self._status = CHANNEL_ONLINE
                    self.ws.fs_send(request)
                else:
                    self._viewers = CHANNEL_NO_VIEWERS
        except Exception as exc:
            log.error("Unable to get viewers. Got error: %s", exc)

    def _get_info(self):
        if not self.smiles:
            try:
                smiles = requests.post(API_URL.format('/smile'), timeout=5)
                if smiles.ok:
                    for smile in smiles.json():
                        self.smiles.append(smile)
            except requests.ConnectionError:
                log.error("Unable to get smiles")


class Sc2tvMessage(object):
    def __init__(self, nickname, text):
        message = [
            u'/chat/message',
            {
                u'from': {
                    u'color': 0,
                    u'name': f'{nickname}'},
                u'text': f'{text}',
                u'to': None,
                u'store': {u'bonuses': [], u'icon': 0, u'subscriptions': []},
                u'id': ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
            }
        ]
        self.data = f'42{json.dumps(message)}'


class TestSc2tv(threading.Thread):
    def __init__(self, main_class):
        super(TestSc2tv, self).__init__()
        self.main_class = main_class  # type: SC2TV
        self.main_class.rest_add('POST', 'push_message', self.send_message)
        self.fs_thread = None

    def run(self):
        while True:
            try:
                thread = self.main_class.channels.items()[0][1]
                if thread.ws:
                    self.fs_thread = thread.ws
                    break
            except:
                continue
        log.info("sc2tv Testing mode online")

    def send_message(self, *args, **kwargs):
        nickname = kwargs.get('nickname', 'super_tester')
        text = kwargs.get('text', 'Kappa 123')

        self.fs_thread.received_message(Sc2tvMessage(nickname, text))


class SC2TV(ChatModule):
    def __init__(self, *args, **kwargs):
        log.info("Initializing funstream chat")
        ChatModule.__init__(self, config=CONF_DICT, gui=CONF_GUI, *args, **kwargs)

        self.socket = CONF_DICT['config']['socket']

    def _test_class(self):
        return TestSc2tv(self)

    def _add_channel(self, chat):
        self.channels[chat] = FsChannel(self.queue, self.socket, chat, chat_module=self)
        self.channels[chat].start()

    def apply_settings(self, **kwargs):
        ChatModule.apply_settings(self, **kwargs)
