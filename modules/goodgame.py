import json, threading, os, ConfigParser, time, Queue
from ws4py.client.threadedclient import WebSocketClient

class ggChat(WebSocketClient):
	def __init__(self, ws, protocols=None, queue=None, id=None):
		super(self.__class__, self).__init__(ws, protocols=None)
		# Received value setting.
		self.source = "gg"
		self.queue = queue
		self.id = id
		# Checking the connection state
		self.pqueue = Queue.Queue()
		
	def opened(self):
		print "[%s] Connection Succesfull" % self.source
		# Sending join channel command to goodgame websocket
		join = json.dumps({'type': "join", 'data': {'channel_id': "15009", 'hidden': "true"}}, sort_keys=False)
		self.send(join)
		# self.ggPing()
		print "[%s] Sent join message" % self.source
		
	def closed(self, code, reason=None):
		print "[%s] Connection Closed Down" % self.source
		
	def received_message(self, mes):
		# Deserialize message to json for easier parsing
		message = json.loads(str(mes))
		if message['type'] == "message":
			# Getting all needed data from received message
			# and sending it to queue for futher message handling
			user = message['data']['user_name']
			text = message['data']['text']
			comp = {'source': self.source, 'user': user, 'text': text}
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
	def __init__(self, queue, address, id):
		threading.Thread.__init__(self)
		# Basic value setting.
		# Daemon is needed so when main programm exits
		# all threads will exit too.
		self.daemon = "True"
		self.queue = queue
		self.address = address
		self.id = id
		
	def run(self):
		# Connecting to goodgame websocket
		ws = ggChat(self.address, protocols=['websocket'], queue=self.queue, id=self.id)
		ws.connect()
		ws.run_forever()

def __init__(queue, pythonFolder):
	print "Initializing goodgame chat"
	
	# Reading config from main directory.
	confFolder=os.path.join(pythonFolder, "conf")
	confFile=os.path.join(confFolder, "chats.cfg")
	config = ConfigParser.RawConfigParser(allow_no_value=True)
	config.read(confFile)
	
	# Checking config file for needed variables
	address = None
	id = None
	for item in config.items("goodgame"):
		if item[0] == 'socket':
			address = item[1]
		elif item[0] == 'channelid':
			id = item[1]
	
	# If any of the value are non-existent then exit the programm with error.
	if (address is None) or (id is None):
		print "Config for goodgame is not correct!"
		exit()
	
	# Creating new thread with queue in place for messaging tranfers
	gg = ggThread(queue, address, id)
	gg.start()