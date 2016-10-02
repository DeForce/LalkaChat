import json
import threading
import os
import requests
import Queue
import re
import logging
from modules.helpers.parser import FlagConfigParser
from ws4py.client.threadedclient import WebSocketClient

logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('goodgame')


class GoodgameMessageHandler(threading.Thread):
    def __init__(self, queue, gg_queue, **kwargs):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.message_queue = queue
        self.gg_queue = gg_queue
        self.source = "gg"

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


class ggChat(WebSocketClient):
    def __init__(self, ws, protocols=None, queue=None, ch_id=None, nick=None, **kwargs):
        super(self.__class__, self).__init__(ws, protocols=protocols)
        # Received value setting.
        self.ch_id = ch_id
        self.gg_queue = Queue.Queue()

        message_handler = GoodgameMessageHandler(queue, self.gg_queue, nick=nick, **kwargs)
        message_handler.start()

    def opened(self):
        log.info("Connection Succesfull")
        # Sending join channel command to goodgame websocket
        join = json.dumps({'type': "join", 'data': {'channel_id': self.ch_id, 'hidden': "true"}}, sort_keys=False)
        self.send(join)
        # self.ggPing()
        log.info("Sent join message")
        
    def closed(self, code, reason=None):
        log.info("Connection Closed Down")
        self.connect()
        
    def received_message(self, mes):
        # Deserialize message to json for easier parsing
        message = json.loads(str(mes))
        self.gg_queue.put(message)


class ggThread(threading.Thread):
    def __init__(self, queue, address, ch_id, nick):
        threading.Thread.__init__(self)
        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = "True"
        self.queue = queue
        self.address = address
        self.nick = nick
        self.ch_id = ch_id
        self.kwargs = {}

    def load_config(self):
        error = False
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

        return error
        
    def run(self):
        if not self.load_config():
            # Connecting to goodgame websocket
            ws = ggChat(self.address, protocols=['websocket'], queue=self.queue, ch_id=self.ch_id, nick=self.nick,
                        **self.kwargs)
            ws.connect()
            ws.run_forever()


class goodgame:
    def __init__(self, queue, python_folder):
        # Reading config from main directory.
        conf_folder = os.path.join(python_folder, "conf")

        log.info("Initializing goodgame chat")
        conf_file = os.path.join(conf_folder, "goodgame.cfg")
        config = FlagConfigParser(allow_no_value=True)
        if not os.path.exists(conf_file):
            config.add_section('gui_information')
            config.set('gui_information', 'category', 'chat')

            config.add_section('config__gui')
            config.set('config__gui', 'for', 'config')
            config.set('config__gui', 'hidden', 'socket')

            config.add_section('config')
            config.set('config', 'socket/hidden', 'ws://chat.goodgame.ru:8081/chat/websocket')
            config.set('config', 'channel_name', 'oxlamon')

            config.write(open(conf_file, 'w'))

        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config}

        config.read(conf_file)
        # Checking config file for needed variables
        conf_tag = 'config'
        address = config.get_or_default(conf_tag, 'socket', 'ws://chat.goodgame.ru:8081/chat/websocket')
        ch_id = config.get_or_default(conf_tag, 'channel_id', None)
        channel_name = config.get_or_default(conf_tag, 'channel_name', 'oxlamon')

        # Creating new thread with queue in place for messaging transfers
        gg = ggThread(queue, address, ch_id, channel_name)
        gg.start()
