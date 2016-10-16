import json
import threading
import time
import re
import requests
import os
import logging
from collections import OrderedDict
from ws4py.client.threadedclient import WebSocketClient
from modules.helpers.modules import ChatModule
from modules.helpers.parser import self_heal
from modules.helpers.system import system_message

logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('sc2tv')
SOURCE = 'fs'
SOURCE_ICON = 'http://funstream.tv/build/images/icon_home.png'
SYSTEM_USER = 'Funstream'
CONF_DICT = OrderedDict()
CONF_DICT['gui_information'] = {'category': 'chat'}
CONF_DICT['config'] = OrderedDict()
CONF_DICT['config']['channel_name'] = 'CHANGE_ME'
CONF_DICT['config']['socket'] = 'ws://funstream.tv/socket.io/'

CONF_GUI = {
    'config': {
        'hidden': ['socket']}}


class FsChat(WebSocketClient):
    def __init__(self, ws, queue, channel_name, protocols=None, smiles=None):
        super(self.__class__, self).__init__(ws, protocols=protocols)
        # Received value setting.
        self.source = SOURCE
        self.queue = queue
        self.channel_name = channel_name

        self.channel_id = self.fs_get_id()

        self.smiles = smiles
        self.smile_regex = ':(\w+|\d+):'

        # Because funstream API is fun, we have to iterate the
        #  requests in "proper" format:
        #
        #  42Iterator["command",{"params":"param"}]
        # ex: 	420["/chat/join",{'channel':"stream/30000"}
        # ex: 	421["/chat/join",{'channel':"stream/30000"}
        # ex: 	429["/chat/join",{'channel':"stream/30000"}
        # ex: 	4210["/chat/join",{'channel':"stream/30000"}
        #
        # Also, funstream API send duplicates of the messages
        #  so we have to ignore the duplicates.
        # We are doing so by creating special array which has
        #  last N buffer of unique ID's
        self.iter = 0
        self.duplicates = []
        self.users = []
        self.bufferForDup = 20

    def opened(self):
        log.info("Websocket Connection Succesfull")

    def closed(self, code, reason=None):
        log.info("Websocket Connection Closed Down")

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
        # Funstream send all kind of different messages
        # Some of them are strange asnwers like "40".
        # For that we are trying to find real messages
        #  which are more than 5 char length.
        #
        # Websocket has it's own type, so we serialise it to string.
        message = str(mes)
        if len(message) > 5:
            # "Fun" messages consists of strange format:
            # 	       43Iter{json}
            # ex:      430{'somedata': 'somedata'}
            # We need to just get the json, so we "regexp" it.
            if re.findall('{.*}', message)[0]:
                # If message does have JSON (some of them dont, dont know why)
                #  we analyze the real "json" message.
                message = json.loads(re.findall('{.*}', message)[0])
                for dict_item in message:
                    # SID type is "start" packet, after that we can join channels,
                    #  at least I think so.
                    if dict_item == 'sid':
                        # "Funstream" has some interesting infrastructure, so
                        #  we first need to find the channel ID from
                        #  nickname of streamer we need to connect to.
                        self.fs_join()
                        self.fs_ping()
                    elif dict_item == 'status':
                        system_message('Joined channel {0}'.format(self.channel_name), self.queue,
                                       source=SOURCE, icon=SOURCE_ICON, from_user=SYSTEM_USER)
                    elif dict_item == 'id':
                        try:
                            self.duplicates.index(message[dict_item])
                        except ValueError:
                            comp = {'source': self.source,
                                    'source_icon': SOURCE_ICON,
                                    'user': message['from']['name'],
                                    'text': message['text'],
                                    'emotes': []}
                            if message['to'] is not None:
                                comp['to'] = message['to']['name']
                                if comp['to'] == self.channel_name:
                                    comp['pm'] = True
                            else:
                                comp['to'] = None

                            smiles_array = re.findall(self.smile_regex, comp['text'])
                            for smile in smiles_array:
                                for smile_find in self.smiles:
                                    if smile_find['code'] == smile:
                                        if self.allow_smile(smile_find, message['store']['subscriptions']):
                                            comp['emotes'].append({'emote_id': smile, 'emote_url': smile_find['url']})

                            self.queue.put(comp)
                            self.duplicates.append(message[dict_item])
                            if len(self.duplicates) > self.bufferForDup:
                                self.duplicates.pop(0)

    def fs_get_id(self):
        # We get ID from POST request to funstream API, and it hopefuly
        #  answers us the correct ID of the channel we need to connect to
        payload = "{'id': null, 'name': \"" + self.channel_name + "\"}"
        request = requests.post("http://funstream.tv/api/user", data=payload)
        if request.status_code == 200:
            channel_id = json.loads(re.findall('{.*}', request.text)[0])['id']
        else:
            error_message = request.json()
            if 'message' in error_message:
                log.error("Unable to get channel ID. {0}".format(error_message['message']))
            else:
                log.error("Unable to get channel ID. No message available")
            channel_id = None
        return channel_id

    def fs_join(self):
        # Because we need to iterate each message we iterate it!
        iter_sio = "42"+str(self.iter)
        self.iter += 1

        # Then we send the message acording to needed format and
        #  hope it joins us
        if self.channel_id:
            join = str(iter_sio) + "[\"/chat/join\", " + json.dumps({'channel': "stream/" + str(self.channel_id)},
                                                                    sort_keys=False) + "]"
            self.send(join)
            system_message('Joining channel {0}'.format(self.channel_name), self.queue,
                           source=SOURCE, icon=SOURCE_ICON, from_user=SYSTEM_USER)
            log.info("Joined channel {0}".format(self.channel_id))

    def fs_ping(self):
        # Because funstream is not your normal websocket they
        #  have own "ping/pong" algorithm, and WE have to send ping.
        #  Yes, I don't know why.
        # We have to send ping message every 30 seconds, or funstream will
        #  disconnect us. So we have to create separate thread for it.
        # Dont understand why server is not sending his own pings, it
        #  would be sooooo easier.
        ping_thread = FsPingThread(self)
        ping_thread.start()


class FsPingThread(threading.Thread):
    def __init__(self, ws):
        threading.Thread.__init__(self)
        self.daemon = "True"
        # Using main websocket
        self.ws = ws

    def run(self):
        # Basically, if we are alive we send every 30 seconds special
        #  coded message, that is very hard to decode:
        #
        #      2
        #
        #  and they answer:
        #
        #      3
        #
        # No idea why.
        while True:
            self.ws.send("2")
            time.sleep(30)


class FsThread(threading.Thread):
    def __init__(self, queue, socket, channel_name):
        threading.Thread.__init__(self)
        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = "True"
        self.queue = queue
        self.socket = socket
        self.channel_name = channel_name
        self.smiles = []

    def run(self):
        # Let us get smiles for sc2tv
        try:
            smiles = requests.post('http://funstream.tv/api/smile')
            if smiles.status_code == 200:
                smiles_answer = smiles.json()
                for smile in smiles_answer:
                    self.smiles.append(smile)
        except requests.ConnectionError:
            log.error("Unable to get smiles")

        # Connecting to funstream websocket
        ws = FsChat(self.socket, self.queue, self.channel_name, protocols=['websocket'], smiles=self.smiles)
        ws.connect()
        ws.run_forever()


class sc2tv(ChatModule):
    def __init__(self, queue, python_folder, **kwargs):
        ChatModule.__init__(self)
        log.info("Initializing funstream chat")

        # Reading config from main directory.
        conf_folder = os.path.join(python_folder, "conf")
        conf_file = os.path.join(conf_folder, "sc2tv.cfg")
        config = self_heal(conf_file, CONF_DICT)
        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config,
                            'config': CONF_DICT,
                            'gui': CONF_GUI}
        # Checking config file for needed variables
        config_tag = 'config'
        socket = config.get(config_tag, 'socket')
        channel_name = config.get(config_tag, 'channel_name')

        # If any of the value are non-existent then exit the programm with error.
        if (socket is None) or (channel_name is None):
            log.critical("Config for funstream is not correct!")

        # Creating new thread with queue in place for messaging tranfers
        fs = FsThread(queue, socket, channel_name)
        fs.start()
