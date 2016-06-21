import json, threading, time, re, requests, os, ConfigParser
from ws4py.client.threadedclient import WebSocketClient

class fsChat(WebSocketClient):
    def __init__(self, ws, queue, nick, protocols=None,):
        super(self.__class__, self).__init__(ws, protocols=None)
        # Received value setting.
        self.source = "fs"
        self.queue = queue
        self.nick = nick

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
        self.bufferForDup = 20

    def opened(self):
        print "[%s] Connection Succesfull" % self.source

    def closed(self, code, reason=None):
        print "[%s] Connection Closed Down" % self.source

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
            if(re.findall('{.*}', message)[0]):
                # If message does have JSON (some of them dont, dont know why)
                #  we analyze the real "json" message.
                message = json.loads(re.findall('{.*}',message)[0])
                for dict in message:
                    # SID type is "start" packet, after that we can join channels,
                    #  at least I think so.
                    if dict == 'sid':
                        # "Funstream" has some interesting infrastructure, so
                        #  we first need to find the channel ID from
                        #  nickname of streamer we need to connect to.
                        self.fsGetId()
                        self.fsJoin()
                        self.fsPing()
                    elif dict == 'id':
                        try:
                            self.duplicates.index(message[dict])
                        except:
                            user = message['from']['name']
                            text = message['text']
                            comp = {'source': self.source, 'user': user, 'text': text}
                            self.queue.put(comp)
                            self.duplicates.append(message[dict])
                            if len(self.duplicates) > self.bufferForDup:
                                self.duplicates.pop(0)

    def fsGetId(self):
        # We get ID from POST request to funstream API, and it hopefuly
        #  answers us the correct ID of the channel we need to connect to
        payload = "{'id': null, 'name': \""+ self.nick + "\"}"
        request = requests.post("http://funstream.tv/api/user", data=payload)
        if request.status_code == 200:
            self.channelID = json.loads(re.findall('{.*}',request.text)[0])['id']

    def fsJoin(self):
        # Because we need to iterate each message we iterate it!
        iter = "42"+str(self.iter)
        self.iter = self.iter+1

        # Then we send the message acording to needed format and
        #  hope it joins us
        join = str(iter)+ "[\"/chat/join\", " + json.dumps({'channel':"stream/" + str(self.channelID)}, sort_keys=False) + "]"
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

    def run(self):
        # Connecting to funstream websocket
        ws = fsChat(self.socket, self.queue, self.nick, protocols=['websocket'])
        ws.connect()
        ws.run_forever()

def __init__(queue, pythonFolder):
    print "Initializing funstream chat"

    # Reading config from main directory.
    confFolder=os.path.join(pythonFolder, "conf")
    confFile=os.path.join(confFolder, "chats.cfg")
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(confFile)

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