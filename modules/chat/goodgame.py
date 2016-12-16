# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import json
import threading
import os
import requests
import Queue
import re
import logging
from collections import OrderedDict
from modules.helper.parser import load_from_config_file
from modules.helper.system import system_message, translate_key, remove_message_by_id, EMOTE_FORMAT
from modules.helper.module import ChatModule
from ws4py.client.threadedclient import WebSocketClient
from gui import MODULE_KEY

logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('goodgame')
SOURCE = 'gg'
SOURCE_ICON = 'http://goodgame.ru/images/icons/favicon.png'
FILE_ICON = os.path.join('img', 'gg.png')
SYSTEM_USER = 'GoodGame'
ID_PREFIX = 'gg_{0}'
CONF_DICT = OrderedDict()
CONF_DICT['gui_information'] = {'category': 'chat'}
CONF_DICT['config'] = OrderedDict()
CONF_DICT['config']['show_pm'] = True
CONF_DICT['config']['channel_name'] = 'CHANGE_ME'
CONF_DICT['config']['socket'] = 'ws://chat.goodgame.ru:8081/chat/websocket'

CONF_GUI = {
    'config': {
        'hidden': ['socket']
    },
    'non_dynamic': ['config.*'],
    'icon': FILE_ICON}


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
        self.smile_regex = ':(\w+|\d+):'
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
        comp = {'id': ID_PREFIX.format(msg['data']['message_id']),
                'source': self.source,
                'source_icon': SOURCE_ICON,
                'user': msg['data']['user_name'],
                'text': msg['data']['text'],
                'emotes': {},
                'type': 'message'}

        self._process_smiles(comp, msg)

        if re.match('^{0},'.format(self.nick).lower(), comp['text'].lower()):
            if self.chat_module.conf_params()['config']['config'].get('show_pm'):
                comp['pm'] = True
        self._send_message(comp)

    def _process_join(self):
        self.ws_class.system_message(translate_key(MODULE_KEY.join(['goodgame', 'join_success'])).format(self.nick),
                                     category='connection')

    def _process_error(self, msg):
        log.info("Received error message: {0}".format(msg))
        if msg['data']['errorMsg'] == 'Invalid channel id':
            self.ws_class.close(reason='INV_CH_ID')
            log.error("Failed to find channel on GoodGame, please check channel name")

    def _process_user_warn(self, msg):
        self.ws_class.system_message(translate_key(MODULE_KEY.join(['goodgame', 'warning'])).format(
            msg['data']['moder_name'], msg['data']['user_name']), category='chat')

    def _process_remove_message(self, msg):
        remove_id = ID_PREFIX.format(msg['data']['message_id'])
        self.message_queue.put(remove_message_by_id([remove_id], text=self.kwargs['settings'].get('remove_text')))

    def _process_user_ban(self, msg):
        if msg['data']['duration']:
            self.ws_class.system_message(translate_key(MODULE_KEY.join(['goodgame', 'ban'])).format(
                msg['data']['moder_name'],
                msg['data']['user_name'],
                msg['data']['duration']/60,
                msg['data']['reason']),
                category='chat')
        else:
            if msg['data']['permanent']:
                self.ws_class.system_message(
                    translate_key(MODULE_KEY.join(['goodgame', 'ban_permanent'])).format(msg['data']['moder_name'],
                                                                                         msg['data']['user_name']),
                    category='chat'
                )
            else:
                self.ws_class.system_message(translate_key(MODULE_KEY.join(['goodgame', 'unban'])).format(
                    msg['data']['moder_name'],
                    msg['data']['user_name']), category='chat')

    def _process_channel_counters(self):
        try:
            self.chat_module.set_viewers(self.chat_module.get_viewers())
        except Exception as exc:
            log.exception(exc)

    def _send_message(self, comp):
        self._post_process_emotes(comp)
        self.message_queue.put(comp)

    @staticmethod
    def _post_process_emotes(comp):
        comp['text'] = re.sub(':(\w+|\d+):', EMOTE_FORMAT.format('\\1'), comp['text'])

    def _process_smiles(self, comp, msg):
        smiles_array = re.findall(self.smile_regex, comp['text'])
        for smile in smiles_array:
            if smile in self.smiles:
                smile_info = self.smiles.get(smile)
                allow = False
                gif = False
                if msg['data']['user_rights'] >= 40:
                    allow = True
                elif msg['data']['user_rights'] >= 20 \
                        and (smile_info['channel_id'] == '0' or smile_info['channel_id'] == '10603'):
                    allow = True
                elif smile_info['channel_id'] == '0' or smile_info['channel_id'] == '10603':
                    if not smile_info['is_premium']:
                        if smile_info['donate_lvl'] == 0:
                            allow = True
                        elif smile_info['donate_lvl'] <= int(msg['data']['payments']):
                            allow = True
                    else:
                        if msg['data']['premium']:
                            allow = True

                for premium in msg['data']['premiums']:
                    if smile_info['channel_id'] == str(premium):
                        if smile_info['is_premium']:
                            allow = True
                            gif = True

                if allow:
                    if smile not in comp['emotes']:
                        if gif and smile_info['urls']['gif']:
                            comp['emotes'][smile] = {'emote_url': smile_info['urls']['gif']}
                        else:
                            comp['emotes'][smile] = {'emote_url': smile_info['urls']['big']}
        emotes_list = []
        for emote, data in comp['emotes'].iteritems():
            emotes_list.append({'emote_id': emote,
                                'emote_url': data['emote_url']})
        comp['emotes'] = emotes_list


class GGChat(WebSocketClient):
    def __init__(self, ws, **kwargs):
        super(self.__class__, self).__init__(ws, heartbeat_freq=kwargs.get('heartbeat_freq'),
                                             protocols=kwargs.get('protocols'))
        # Received value setting.
        self.ch_id = kwargs.get('ch_id')
        self.queue = kwargs.get('queue')
        self.gg_queue = Queue.Queue()

        self.main_thread = kwargs.get('main_thread')
        self.chat_module = kwargs.get('chat_module')
        self.crit_error = False

        message_handler = GoodgameMessageHandler(self, gg_queue=self.gg_queue, **kwargs)
        message_handler.start()

    def opened(self):
        success_msg = "Connection Successful"
        log.info(success_msg)
        self.chat_module.set_online()
        try:
            self.chat_module.set_viewers(self.chat_module.get_viewers())
        except Exception as exc:
            log.exception(exc)
        self.system_message(translate_key(MODULE_KEY.join(['goodgame', 'connection_success'])), category='connection')
        # Sending join channel command to goodgame websocket
        join = json.dumps({'type': "join", 'data': {'channel_id': self.ch_id, 'hidden': "true"}}, sort_keys=False)
        self.send(join)
        # self.ggPing()
        log.info("Sent join message")

    def closed(self, code, reason=None):
        log.info("Connection Closed Down")
        self.chat_module.set_offline()
        if 'INV_CH_ID' in reason:
            self.crit_error = True
        else:
            self.system_message(translate_key(MODULE_KEY.join(['goodgame', 'connection_died'])), category='connection')
            timer = threading.Timer(5.0, self.main_thread.connect)
            timer.start()

    def received_message(self, mes):
        # Deserialize message to json for easier parsing
        self.gg_queue.put(json.loads(str(mes)))

    def system_message(self, msg, category='system'):
        system_message(msg, self.queue, SOURCE,
                       icon=SOURCE_ICON, from_user=SYSTEM_USER, category=category)


class GGThread(threading.Thread):
    def __init__(self, queue, address, nick, **kwargs):
        threading.Thread.__init__(self)
        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = True
        self.queue = queue
        self.address = address
        self.nick = nick
        self.ch_id = None
        self.kwargs = kwargs

    def load_config(self):
        try:
            self.kwargs['smiles'] = {}
            smile_request = requests.get("http://api2.goodgame.ru/smiles")
            next_page = smile_request.json()['_links']['first']['href']
            while True:
                req_smile = requests.get(next_page)
                if req_smile.status_code == 200:
                    req_smile_answer = req_smile.json()

                    for smile in req_smile_answer['_embedded']['smiles']:
                        self.kwargs['smiles'][smile['key']] = smile

                    if 'next' in req_smile_answer['_links']:
                        next_page = req_smile_answer['_links']['next']['href']
                    else:
                        break
        except Exception as exc:
            log.error("Unable to download smiles, error {0}\nArgs: {1}".format(exc.message, exc.args))

        try:
            if self.ch_id:
                request = requests.get("http://api2.goodgame.ru/streams/{0}".format(self.ch_id))
                if request.status_code == 200:
                    channel_name = request.json()['channel']['key']
                    if self.nick != channel_name:
                        self.nick = channel_name
            else:
                request = requests.get("http://api2.goodgame.ru/streams/{0}".format(self.nick))
                if request.status_code == 200:
                    self.ch_id = request.json()['channel']['id']
        except Exception as exc:
            log.warning("Unable to get channel name, error {0}\nArgs: {1}".format(exc.message, exc.args))

        return True

    def run(self):
        self.connect()

    def connect(self):
        try_count = 0
        while True:
            try_count += 1
            log.info("Connecting, try {0}".format(try_count))
            if self.load_config():
                # Connecting to goodgame websocket
                ws = GGChat(self.address, protocols=['websocket'], queue=self.queue, ch_id=self.ch_id, nick=self.nick,
                            heartbeat_freq=30, main_thread=self, **self.kwargs)
                try:
                    ws.connect()
                    ws.run_forever()
                    log.debug("Connection closed")
                    break
                except Exception as exc:
                    log.exception(exc)


class goodgame(ChatModule):
    def __init__(self, queue, python_folder, **kwargs):
        ChatModule.__init__(self)
        # Reading config from main directory.
        conf_folder = os.path.join(python_folder, "conf")

        log.info("Initializing goodgame chat")
        conf_file = os.path.join(conf_folder, "goodgame.cfg")
        config = load_from_config_file(conf_file, CONF_DICT)
        self._conf_params.update(
            {'folder': conf_folder, 'file': conf_file,
             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
             'parser': config,
             'config': CONF_DICT,
             'gui': CONF_GUI,
             'settings': {}})

        self.queue = queue
        self.host = CONF_DICT['config']['socket']
        self.channel_name = CONF_DICT['config']['channel_name']
        self.gg = None

    def load_module(self, *args, **kwargs):
        ChatModule.load_module(self, *args, **kwargs)
        if 'webchat' in self._loaded_modules:
            self._loaded_modules['webchat']['class'].add_depend('goodgame')
        self._conf_params['settings']['remove_text'] = self.get_remove_text()
        # Creating new thread with queue in place for messaging transfers
        gg = GGThread(self.queue, self.host, self.channel_name,
                      settings=self._conf_params['settings'], chat_module=self)
        self.gg = gg
        gg.start()

    def get_remove_text(self):
        if self._loaded_modules['webchat']['style_settings']['keys'].get('remove_message'):
            return self._loaded_modules['webchat']['style_settings']['keys'].get('remove_text')
        return None

    def get_viewers(self):
        streams_url = 'http://api2.goodgame.ru/streams/{0}'.format(self.gg.ch_id)
        try:
            request = requests.get(streams_url)
            if request.status_code == 200:
                return request.json().get('player_viewers')
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get user count, error {0}\nArgs: {1}".format(exc.message, exc.args))

    def apply_settings(self, **kwargs):
        ChatModule.apply_settings(self, **kwargs)
        if 'webchat' in kwargs.get('from_depend', []):
            self._conf_params['settings']['remove_text'] = self.get_remove_text()
