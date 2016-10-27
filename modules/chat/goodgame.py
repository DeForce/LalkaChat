import json
import threading
import os
import requests
import Queue
import re
import logging
import time
from collections import OrderedDict
from modules.helper.parser import self_heal
from modules.helper.system import system_message
from modules.helper.modules import ChatModule
from ws4py.client.threadedclient import WebSocketClient

logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('goodgame')
SOURCE = 'gg'
SOURCE_ICON = 'http://goodgame.ru/images/icons/favicon.png'
SYSTEM_USER = 'GoodGame'
CONF_DICT = OrderedDict()
CONF_DICT['gui_information'] = {'category': 'chat'}
CONF_DICT['config'] = OrderedDict()
CONF_DICT['config']['channel_name'] = 'CHANGE_ME'
CONF_DICT['config']['socket'] = 'ws://chat.goodgame.ru:8081/chat/websocket'

CONF_GUI = {
    'config': {
        'hidden': ['socket']}}


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

    def run(self):
        while True:
            self.process_message(self.gg_queue.get())

    def process_message(self, msg):
        if msg['type'] == "message":
            # Getting all needed data from received message
            # and sending it to queue for further message handling
            comp = {'source': self.source,
                    'source_icon': SOURCE_ICON,
                    'user': msg['data']['user_name'],
                    'text': msg['data']['text'],
                    'emotes': []}

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
                                comp['emotes'].append({'emote_id': smile, 'emote_url': smile_info['urls']['gif']})
                            else:
                                comp['emotes'].append({'emote_id': smile, 'emote_url': smile_info['urls']['big']})

            if re.match('^{0},'.format(self.nick).lower(), comp['text'].lower()):
                comp['pm'] = True
            self.message_queue.put(comp)
        elif msg['type'] == 'success_join':
            self.ws_class.system_message('Successfully joined channel {0}'.format(self.nick))
        elif msg['type'] == 'error':
            log.info("Received error message: {0}".format(msg))
            if msg['data']['errorMsg'] == 'Invalid channel id':
                self.ws_class.close(reason='INV_CH_ID')
                log.error("Failed to find channel on GoodGame, please check channel name")


class GGChat(WebSocketClient):
    def __init__(self, ws, **kwargs):
        super(self.__class__, self).__init__(ws, heartbeat_freq=kwargs.get('heartbeat_freq'),
                                             protocols=kwargs.get('protocols'))
        # Received value setting.
        self.ch_id = kwargs.get('ch_id')
        self.queue = kwargs.get('queue')
        self.gg_queue = Queue.Queue()

        self.main_thread = kwargs.get('main_thread')
        self.crit_error = False

        message_handler = GoodgameMessageHandler(self, gg_queue=self.gg_queue, **kwargs)
        message_handler.start()

    def opened(self):
        success_msg = "Connection Successful"
        log.info(success_msg)
        self.system_message(success_msg)
        # Sending join channel command to goodgame websocket
        join = json.dumps({'type': "join", 'data': {'channel_id': self.ch_id, 'hidden': "true"}}, sort_keys=False)
        self.send(join)
        # self.ggPing()
        log.info("Sent join message")
        
    def closed(self, code, reason=None):
        log.info("Connection Closed Down")
        if 'INV_CH_ID' in reason:
            self.crit_error = True
        else:
            self.system_message("Connection died, trying to reconnect")
            timer = threading.Timer(5.0, self.main_thread.connect)
            timer.start()

    def received_message(self, mes):
        # Deserialize message to json for easier parsing
        self.gg_queue.put(json.loads(str(mes)))

    def system_message(self, msg):
        system_message(msg, self.queue, SOURCE,
                       icon=SOURCE_ICON, from_user=SYSTEM_USER)


class GGThread(threading.Thread):
    def __init__(self, queue, address, nick):
        threading.Thread.__init__(self)
        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = True
        self.queue = queue
        self.address = address
        self.nick = nick
        self.ch_id = None
        self.kwargs = {}

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
        config = self_heal(conf_file, CONF_DICT)
        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config,
                            'config': CONF_DICT,
                            'gui': CONF_GUI}

        # Checking config file for needed variables
        conf_tag = 'config'
        address = config.get(conf_tag, 'socket')
        channel_name = config.get(conf_tag, 'channel_name')
        # ch_id

        # Creating new thread with queue in place for messaging transfers
        gg = GGThread(queue, address, channel_name)
        gg.start()
