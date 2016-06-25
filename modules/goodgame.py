import json
import threading
import os
import ConfigParser
import requests
import Queue
import re
from ws4py.client.threadedclient import WebSocketClient


class ggChat(WebSocketClient):
    def __init__(self, ws, protocols=None, queue=None, id=None, nick=None, smiles=None):
        super(self.__class__, self).__init__(ws, protocols=None)
        # Received value setting.
        self.source = "gg"
        self.queue = queue
        self.id = id
        self.nick = nick
        # Checking the connection state
        self.pqueue = Queue.Queue()

        self.smiles = smiles
        self.smile_regex = ':(\w+|\d+):'

    def opened(self):
        print "[%s] Connection Succesfull" % self.source
        # Sending join channel command to goodgame websocket
        join = json.dumps({'type': "join", 'data': {'channel_id': self.id, 'hidden': "true"}}, sort_keys=False)
        self.send(join)
        # self.ggPing()
        print "[%s] Sent join message" % self.source
        
    def closed(self, code, reason=None):
        print "[%s] Connection Closed Down" % self.source
        self.connect()
        
    def received_message(self, mes):
        # Deserialize message to json for easier parsing
        message = json.loads(str(mes))
        if message['type'] == "message":
            # Getting all needed data from received message
            # and sending it to queue for further message handling
            comp = {'source': self.source,
                    'user': message['data']['user_name'],
                    'text': message['data']['text']}

            # print message
            emotes = []
            smiles_array = re.findall(self.smile_regex, comp['text'])
            for smile in smiles_array:
                for smile_find in self.smiles:
                    if smile_find['key'] == smile:
                        # print smile_find
                        allow = False
                        if message['data']['user_rights'] >= 40:
                            allow = True
                        elif message['data']['user_rights'] >= 20 \
                                and (smile_find['channel_id'] == '0' or smile_find['channel_id'] == '10603'):
                            allow = True
                        elif smile_find['channel_id'] == '0' or smile_find['channel_id'] == '10603':
                            if smile_find['donate_lvl'] == 0:
                                allow = True
                            elif smile_find['donate_lvl'] <= int(message['data']['payments']):
                                allow = True

                        for premium in message['data']['premiums']:
                            if smile_find['channel_id'] == str(premium):
                                if smile_find['is_premium']:
                                    # print smile_find['is_premium']
                                    allow = True

                        if allow:
                            if smile not in emotes:
                                emotes.append({'emote_id': smile, 'emote_url': smile_find['urls']['big']})
            comp['emotes'] = emotes

            if re.match('^{0},'.format(self.nick).lower(), comp['text'].lower()):
                comp['pm'] = True
            self.queue.put(comp)

        # elif message['type'] == "channel_counters":
            # self.pqueue.put(True)
            # print "not put"
            
    # def ggPing(self):
        # pingThr = pingThread(self, self.pqueue)
        # pingThr.start()

# class pingThread(threading.Thread):
    # def __init__(self, ws, pqueue):
        # threading.Thread.__init__(self)
        # self.daemon = "True"
        # self.pqueue = pqueue
        # self.connect = True
        # Using main websocket
        # self.ws = ws
    
    # def run(self):
        # while True:
            # print "HelloWorld"
            # print self.connect
            # if self.connect == True:
                # time.sleep(5)
                # self.connect = False
                # print "SENT PING"
                # self.ws.ping('')
            # else:
                # print "TRYING TO RECONNECT"
                # ws.connect()
            # try:
                # self.connect = self.pqueue.get()
            # except:
                # self.connect = False
            
            
class ggThread(threading.Thread):
    def __init__(self, queue, address, id, nick):
        threading.Thread.__init__(self)
        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = "True"
        self.queue = queue
        self.address = address
        self.nick = nick
        self.id = id
        self.smiles = []
        
    def run(self):
        # Get the fucking smiles
        try:
            smile_request = requests.get("http://api2.goodgame.ru/smiles")
            next_page = smile_request.json()['_links']['first']['href']
            while True:
                req_smile = requests.get(next_page)
                if req_smile.status_code == 200:
                    req_smile_answer = req_smile.json()

                    for smile in req_smile_answer['_embedded']['smiles']:
                        self.smiles.append(smile)

                    if 'next' in req_smile_answer['_links']:
                        next_page = req_smile_answer['_links']['next']['href']
                    else:
                        break
        except Exception as exc:
            print exc
            print "Unable to download smiles, YAY"

        # Connecting to goodgame websocket
        ws = ggChat(self.address, protocols=['websocket'], queue=self.queue, id=self.id, nick=self.nick,
                    smiles=self.smiles)
        ws.connect()
        ws.run_forever()


def __init__(queue, python_folder):
    print "Initializing goodgame chat"
    
    # Reading config from main directory.
    conf_folder = os.path.join(python_folder, "conf")
    conf_file = os.path.join(conf_folder, "chats.cfg")
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(conf_file)

    # Checking config file for needed variables
    address = None
    ch_id = None
    for item in config.items("goodgame"):
        if item[0] == 'socket':
            address = item[1]
        if item[0] == 'channelid':
            ch_id = item[1]
            try:
                request = requests.get("http://api2.goodgame.ru/streams/"+ch_id)
                if request.status_code == 200:
                    # print type(request.json())
                    channel_name = request.json()['channel']['key']
                    print request.json()
            except:
                print "Issue with goodgame"
                if ch_id is None:
                    exit()
        if item[0] == 'channelname':
            channel_name = item[1]
            try:
                request = requests.get("http://api2.goodgame.ru/streams/"+channel_name)
                if request.status_code == 200:
                    # print type(request.json())
                    ch_id = request.json()['channel']['id']
                    print request.json()
            except:
                print "Issue with goodgame"
                if ch_id is None:
                    exit()
    # If any of the value are non-existent then exit the programm with error.
    if (address is None) or (ch_id is None):
        print "Config for goodgame is not correct!"
        exit()
    
    # Creating new thread with queue in place for messaging tranfers
    gg = ggThread(queue, address, ch_id, channel_name)
    gg.start()
