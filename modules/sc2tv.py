import json
import threading
import time
import re
import requests
import os
import ConfigParser
from ws4py.client.threadedclient import WebSocketClient


class fsChat(WebSocketClient):
    def __init__(self, ws, queue, nick, protocols=None, smiles=[]):
        super(self.__class__, self).__init__(ws, protocols=None)
        # Received value setting.
        self.source = "fs"
        self.queue = queue
        self.nick = nick

        self.smiles = smiles
        self.smile_regex = ':(\w+|\d+):'

        # Because funstream API is fun, we have to iterate the
        #  requests in "proper" format:
        #
        #			42Iterator["command",{"params":"param"}]
        #ex: 	420["/chat/join",{'channel':"stream/30000"}
        #ex: 	421["/chat/join",{'channel':"stream/30000"}
        #ex: 	429["/chat/join",{'channel':"stream/30000"}
        #ex: 	4210["/chat/join",{'channel':"stream/30000"}
        #
        # Also, funstream API send duplicates of the messages
        #  so we have to ignore the duplicates.
        # We are doing so by creating special array which has
        #  last N buffer of unique ID's
        self.iter = 0
        self.fsGetId()
        self.duplicates = []
        self.users = []
        self.bufferForDup = 20

    def opened(self):
        print "[%s] Connection Succesfull" % self.source

    def closed(self, code, reason=None):
        print "[%s] Connection Closed Down" % self.source

    def allow_smile(self, smile, user_id):
        allow = False

        if smile['level'] == 0:
            allow = True
        # else:
        #     user_match = False
        #     for user_iter in self.users:
        #         if user_iter['id'] == user_id:
        #             user_match = True
        #
        #     if not user_match:
        #         try:
        #             user_id = {'id': user_id}
        #             req_user = requests.post('http://funstream.tv/api/user/full', json=user_id)
        #             if req_user.status_code == 200:
        #                 req_user_answer = req_user.json()
        #                 print "HelloWorld"
        #                 print req_user_answer
        #
        #         except:
        #             print "Unable to get smiles"
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
                        self.fsGetId()
                        self.fsJoin()
                        self.fsPing()
                    elif dict_item == 'id':
                        try:
                            self.duplicates.index(message[dict_item])
                        except:
                            comp = {'source': self.source,
                                    'user': message['from']['name'],
                                    'text': message['text']}
                            if message['to'] is not None:
                                comp['to'] = message['to']['name']
                                if comp['to'] == self.nick:
                                    comp['pm'] = True
                            else:
                                comp['to'] = None

                            emotes = []
                            smiles_array = re.findall(self.smile_regex, comp['text'])
                            for smile in smiles_array:
                                for smile_find in self.smiles:
                                    if smile_find['code'] == smile:
                                        if self.allow_smile(smile_find, message['from']['id']):
                                            emotes.append({'emote_id': smile, 'emote_url': smile_find['url']})
                            comp['emotes'] = emotes

                            self.queue.put(comp)
                            self.duplicates.append(message[dict_item])
                            if len(self.duplicates) > self.bufferForDup:
                                self.duplicates.pop(0)

    def fsGetId(self):
        # We get ID from POST request to funstream API, and it hopefuly
        #  answers us the correct ID of the channel we need to connect to
        payload = "{'id': null, 'name': \"" + self.nick + "\"}"
        request = requests.post("http://funstream.tv/api/user", data=payload)
        if request.status_code == 200:
            self.channelID = json.loads(re.findall('{.*}', request.text)[0])['id']

    def fsJoin(self):
        # Because we need to iterate each message we iterate it!
        iter = "42"+str(self.iter)
        self.iter = self.iter+1

        # Then we send the message acording to needed format and
        #  hope it joins us
        join = str(iter) + "[\"/chat/join\", " + json.dumps({'channel': "stream/" + str(self.channelID)}, sort_keys=False) + "]"
        self.send(join)
        print "[%s] Joined channel %s" % (self.source, self.channelID)

    def fsPing(self):
        # Because funstream is not your normal websocket they
        #  have own "ping/pong" algorithm, and WE have to send ping.
        #  Yes, I don't know why.
        # We have to send ping message every 30 seconds, or funstream will
        #  disconnect us. So we have to create separate thread for it.
        # Dont understand why server is not sending his own pings, it
        #  would be sooooo easier.
        pingThr = pingThread(self)
        pingThr.start()


class pingThread(threading.Thread):
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


class fsThread(threading.Thread):
    def __init__(self, queue, socket, nick):
        threading.Thread.__init__(self)
        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = "True"
        self.queue = queue
        self.socket = socket
        self.nick = nick
        self.smiles = []

    def run(self):
        # Let us get smiles for sc2tv
        try:
            smiles = requests.post('http://funstream.tv/api/smile')
            if smiles.status_code == 200:
                smiles_answer = smiles.json()
                for smile in smiles_answer:
                    self.smiles.append(smile)
        except:
            print "Unable to get smiles"

        # Connecting to funstream websocket
        ws = fsChat(self.socket, self.queue, self.nick, protocols=['websocket'], smiles=self.smiles,)
        ws.connect()
        ws.run_forever()


def __init__(queue, python_folder):
    print "Initializing funstream chat"

    # Reading config from main directory.
    conf_folder = os.path.join(python_folder, "conf")
    conf_file = os.path.join(conf_folder, "chats.cfg")
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(conf_file)

    # Checking config file for needed variables
    socket = None
    nick = None
    for item in config.items("sc2tv"):
        if item[0] == 'socket':
            socket = item[1]
        elif item[0] == 'nick':
            nick = item[1]

    # If any of the value are non-existent then exit the programm with error.
    if (socket is None) or (nick is None):
        print "Config for funstream is not correct!"
        exit()

    # Creating new thread with queue in place for messaging tranfers
    fs = fsThread(queue, socket, nick)
    fs.start()
