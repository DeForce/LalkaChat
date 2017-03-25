# Copyright (C) 2016   CzT/Vladislav Ivanov
import json
import random
import string
import threading
import time
import re
import requests
import os
import logging
from collections import OrderedDict
from ws4py.client.threadedclient import WebSocketClient
from modules.helper.module import ChatModule
from modules.helper.parser import load_from_config_file
from modules.helper.system import system_message, translate_key, EMOTE_FORMAT
from gui import MODULE_KEY

logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('sc2tv')
SOURCE = 'fs'
SOURCE_ICON = 'http://funstream.tv/build/images/icon_home.png'
FILE_ICON = os.path.join('img', 'fs.png')
SYSTEM_USER = 'Peka2.tv'
SMILE_REGEXP = r':(\w+|\d+):'
SMILE_FORMAT = ':{}:'

PING_DELAY = 10

CONF_DICT = OrderedDict()
CONF_DICT['gui_information'] = {'category': 'chat'}
CONF_DICT['config'] = OrderedDict()
CONF_DICT['config']['show_pm'] = True
CONF_DICT['config']['socket'] = 'ws://funstream.tv/socket.io/'
CONF_DICT['config']['show_channel_names'] = True
CONF_DICT['config']['channels_list'] = []

CONF_GUI = {
    'config': {
        'hidden': ['socket'],
        'channels_list': {
            'view': 'list',
            'addable': 'true'
        },
    },
    'non_dynamic': ['config.socket'],
    'icon': FILE_ICON}


class FsChat(WebSocketClient):
    def __init__(self, ws, queue, channel_name, **kwargs):
        super(self.__class__, self).__init__(ws, protocols=kwargs.get('protocols', None))
        # Received value setting.
        self.source = SOURCE
        self.queue = queue
        self.channel_name = channel_name
        self.main_thread = kwargs.get('main_thread')  # type: FsThread
        self.chat_module = kwargs.get('chat_module')
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
        self.fs_system_message(translate_key(MODULE_KEY.join(['sc2tv', 'connection_success'])), category='connection')

    def closed(self, code, reason=None):
        """
        Codes used by LC
        4000 - Normal disconnect by LC
        4001 - Invalid Channel ID

        :param code: 
        :param reason: 
        """
        self.chat_module.set_offline(self.channel_name)
        if code in [4000, 4001]:
            self.crit_error = True
            self.fs_system_message(translate_key(
                MODULE_KEY.join(['sc2tv', 'connection_closed'])).format(self.channel_name),
                                category='connection')
        else:
            log.info("Websocket Connection Closed Down")
            self.fs_system_message(
                translate_key(MODULE_KEY.join(['sc2tv', 'connection_died'])).format(self.channel_name),
                category='connection')
            timer = threading.Timer(5.0, self.main_thread.connect)
            timer.start()

    def fs_system_message(self, message, category='system'):
        system_message(message, self.queue, source=SOURCE, icon=SOURCE_ICON, from_user=SYSTEM_USER, category=category)

    @staticmethod
    def allow_smile(smile, subscriptions):
        allow = False

        if smile['user']:
            channel_id = smile['user']['id']
            for sub in subscriptions:
                if sub == channel_id:
                    allow = True
        else:
            allow = True

        return allow

    def received_message(self, mes):
        if mes.data == '40':
            return
        if mes.data in ['2', '3']:
            return
        regex = re.match('(\d+)(.*)', mes.data)
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
        payload = {
            'id': None,
            'name': self.channel_name
        }
        try:
            request = requests.post("http://funstream.tv/api/user", data=payload, timeout=5)
            if request.status_code == 200:
                channel_id = json.loads(re.findall('{.*}', request.text)[0])['id']
                return channel_id
            else:
                error_message = request.json()
                if 'message' in error_message:
                    log.error("Unable to get channel ID. {0}".format(error_message['message']))
                    self.closed(0, 'INV_CH_ID')
                else:
                    log.error("Unable to get channel ID. No message available")
                    self.closed(0, 'INV_CH_ID')
        except requests.ConnectionError:
            log.info("Unable to get information from api")
        return None

    def fs_join(self):
        # Then we send the message acording to needed format and
        #  hope it joins us
        if self.channel_id:
            payload = [
                '/chat/join',
                {
                    'channel': 'stream/{0}'.format(str(self.channel_id))
                }
            ]
            self.fs_send(payload)

            msg_joining = translate_key(MODULE_KEY.join(['sc2tv', 'joining']))
            self.fs_system_message(msg_joining.format(self.channel_name), category='connection')
            log.info(msg_joining.format(self.channel_id))

    def fs_send(self, payload):
        iter_sio = "42"+str(self.iter)

        self.send('{iter}{payload}'.format(iter=iter_sio,
                                           payload=json.dumps(payload)))
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
            comp = {'source': self.source,
                    'source_icon': SOURCE_ICON,
                    'user': message['from']['name'],
                    'text': message['text'],
                    'emotes': [],
                    'type': 'message'}
            if message['to'] is not None:
                comp['to'] = message['to']['name']
                if comp['to'] == self.channel_name:
                    if self.chat_module.conf_params()['config']['config'].get('show_pm'):
                        comp['pm'] = True
            else:
                comp['to'] = None

            smiles_array = re.findall(SMILE_REGEXP, comp['text'])
            for smile in smiles_array:
                for smile_find in self.smiles:
                    if smile_find['code'] == smile.lower():
                        if self.allow_smile(smile_find, message['store']['subscriptions']):
                            comp['text'] = comp['text'].replace(SMILE_FORMAT.format(smile),
                                                                EMOTE_FORMAT.format(smile))
                            comp['emotes'].append({'emote_id': smile, 'emote_url': smile_find['url']})

            self.duplicates.append(message['id'])
            if len(self.duplicates) > self.bufferForDup:
                self.duplicates.pop(0)
            self._send_message(comp)

    def _process_joined(self):
        self.chat_module.set_online(self.channel_name)
        self.fs_system_message(
            translate_key(MODULE_KEY.join(['sc2tv', 'join_success'])).format(self.channel_name), category='connection')

    def _process_channel_list(self, message):
        self.chat_module.set_viewers(self.channel_name, message['result']['amount'])

    def _post_process_multiple_channels(self, message):
        if self.chat_module.conf_params()['config']['config']['show_channel_names']:
            message['channel_name'] = self.channel_name

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
            self.ws.send("2")
            self.ws.chat_module.get_viewers(self.ws)
            time.sleep(PING_DELAY)


class FsThread(threading.Thread):
    def __init__(self, queue, socket, channel_name, **kwargs):
        threading.Thread.__init__(self)
        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = "True"
        self.queue = queue
        self.socket = socket
        self.channel_name = channel_name
        self.chat_module = kwargs.get('chat_module')
        self.smiles = []
        self.ws = None
        self.kwargs = kwargs

    def run(self):
        self.connect()

    def connect(self):
        # Connecting to funstream websocket
        try_count = 0
        while True:
            try_count += 1
            log.info("Connecting, try {0}".format(try_count))
            if not self.smiles:
                try:
                    smiles = requests.post('http://funstream.tv/api/smile', timeout=5)
                    if smiles.status_code == 200:
                        smiles_answer = smiles.json()
                        for smile in smiles_answer:
                            self.smiles.append(smile)
                except requests.ConnectionError:
                    log.error("Unable to get smiles")
            self.ws = FsChat(self.socket, self.queue, self.channel_name, protocols=['websocket'], smiles=self.smiles,
                             main_thread=self, **self.kwargs)
            if self.ws.crit_error:
                log.critical("Got critical error, halting")
                break
            elif self.ws.channel_id and self.smiles:
                self.ws.connect()
                self.ws.run_forever()
                break
            time.sleep(5)

    def stop(self):
        self.ws.send("11")
        self.ws.close(4000, reason="CLOSE_OK")


class Sc2tvMessage(object):
    def __init__(self, nickname, text):
        message = [
            u'/chat/message',
            {
                u'from': {
                    u'color': 0,
                    u'name': u'{}'.format(nickname)},
                u'text': u'{}'.format(text),
                u'to': None,
                u'store': {u'bonuses': [], u'icon': 0, u'subscriptions': []},
                u'id': ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
            }
        ]
        self.data = '42{}'.format(json.dumps(message))


class TestSc2tv(threading.Thread):
    def __init__(self, main_class):
        super(TestSc2tv, self).__init__()
        self.main_class = main_class  # type: sc2tv
        self.main_class.rest_add('POST', 'push_message', self.send_message)
        self.fs_thread = None

    def run(self):
        while True:
            try:
                thread = self.main_class.fs_thread.items()[0][1]
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


class sc2tv(ChatModule):
    def __init__(self, queue, python_folder, **kwargs):
        ChatModule.__init__(self)
        log.info("Initializing funstream chat")

        # Reading config from main directory.
        conf_folder = os.path.join(python_folder, "conf")
        conf_file = os.path.join(conf_folder, "sc2tv.cfg")
        config = load_from_config_file(conf_file, CONF_DICT)
        self._conf_params.update(
            {'folder': conf_folder, 'file': conf_file,
             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
             'parser': config,
             'config': CONF_DICT,
             'gui': CONF_GUI})

        self.queue = queue
        self.socket = CONF_DICT['config']['socket']
        self.channels_list = CONF_DICT['config']['channels_list']
        self.fs_thread = {}

        if len(self.channels_list) == 1:
            if CONF_DICT['config']['show_channel_names']:
                CONF_DICT['config']['show_channel_names'] = False

        self.testing = kwargs.get('testing')
        if self.testing:
            self.testing = TestSc2tv(self)

    def load_module(self, *args, **kwargs):
        ChatModule.load_module(self, *args, **kwargs)
        # Creating new thread with queue in place for messaging transfers
        for channel in self.channels_list:
            self._set_chat_online(channel)
        if self.testing:
            self.testing.start()

    def get_viewers(self, ws):
        user_data = {'name': ws.channel_name}
        status_data = {'slug': ws.channel_name}
        request = ['/chat/channel/list', {'channel': 'stream/{0}'.format(str(ws.channel_id))}]

        try:
            user_request = requests.post('http://funstream.tv/api/user', timeout=5, data=user_data)
            if user_request.status_code == 200:
                status_data['slug'] = user_request.json()['slug']
        except requests.ConnectionError:
            log.error("Unable to get smiles")

        try:
            status_request = requests.post('http://funstream.tv/api/stream', timeout=5, data=status_data)
            if status_request.status_code == 200:
                if status_request.json()['online']:
                    self.set_online(ws.channel_name)
                    ws.fs_send(request)
                else:
                    self.set_viewers(ws.channel_name, 'N/A')

        except requests.ConnectionError:
            log.error("Unable to get smiles")

    def _set_chat_offline(self, chat):
        ChatModule.set_chat_offline(self, chat)
        try:
            self.fs_thread[chat].stop()
        except Exception as exc:
            log.debug(exc)
        del self.fs_thread[chat]

    def _set_chat_online(self, chat):
        ChatModule.set_chat_online(self, chat)
        self.fs_thread[chat] = FsThread(self.queue, self.socket, chat, chat_module=self)
        self.fs_thread[chat].start()

    def apply_settings(self, **kwargs):
        ChatModule.apply_settings(self, **kwargs)
        self._check_chats(self.fs_thread.keys())
