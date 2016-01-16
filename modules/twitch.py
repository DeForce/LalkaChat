import irc.client, threading, os, sys, ConfigParser, random, requests

class IRC(irc.client.SimpleIRCClient):
	def __init__(self, queue, channel):
		irc.client.SimpleIRCClient.__init__(self)
		# Basic variables, twitch channel are IRC so #channel
		self.channel = "#" + channel
		self.source = "tw"
		self.queue = queue
		
	def on_connect(self, connection, event):
		print "[%s] Connected" % self.source
		
	def on_welcome(self, connection, event):
		print "[%s] Welcome Received" % self.source
		# After we receive IRC Welcome we send request for join and
		#  request for Capabilites (Twitch color, Display Name,
		#  Subscriber, etc)
		connection.join(self.channel)
		connection.cap('REQ',':twitch.tv/tags')

	def on_join(self, connection, event):
		print "[%s] Joined %s channel" % (self.source, self.channel)
		
	def on_pubmsg(self, connection, event):
		# After we receive the message we have to process the tags
		# There are multiple things that are available, but 
		#  for now we use only display-name, which is case-able.
		# Also, there is slight problem with some users, they dont have
		#  the display-name tag, so we have to check their "real" username
		#  and capitalize it because twitch does so, so we do the same.
		for tag in event.tags:
			if tag['key'] == 'display-name':
				if tag['value'] is None:
					# If there is not display-name then we strip the user
					#  from the string and use it as it is.
					user = event.source.split('!')[0].capitalize()
				else:
					user = tag['value']
		
		# Then we comp the message and send it to queue for message handling.
		text = event.arguments[0]
		print event.source
		comp = {'source': self.source, 'user': user, 'text': text}
			
		self.queue.put(comp)
		
class twThread(threading.Thread):
	def __init__(self, queue, host, port, channel):
		threading.Thread.__init__(self)
		# Basic value setting.
		# Daemon is needed so when main programm exits
		# all threads will exit too.
		self.daemon = "True"
		self.queue = queue
		
		self.host = host
		self.port = port
		self.channel = channel
		
		# For anonymous log in Twitch wants username in special format:
		#
		#        justinfan(14d)
		#    ex: justinfan54826341875412
		#
		nickLength = 14
		self.nickname = "justinfan"
		
		for number in range(0, nickLength):
			self.nickname = self.nickname + str(random.randint(0, 9))
	
	def run(self):
		# We are connecting via IRC handler.
		ircClient = IRC(self.queue, self.channel)
		ircClient.connect(self.host, self.port, self.nickname)
		ircClient.start()
		# print dir(IRCCat)
		# irc.connect()

def __init__(queue, pythonFolder):
	print "Initializing twitch chat"
	
	# Reading config from main directory.
	confFolder=os.path.join(pythonFolder, "conf")
	confFile=os.path.join(confFolder, "chats.cfg")
	config = ConfigParser.RawConfigParser(allow_no_value=True)
	config.read(confFile)
	
	# Checking config file for needed variables
	# host, port, channel = tuple ( [None] * 3 ) ?!?!?!?!
	host = None
	port = None
	channel = None
	
	# If any of the value are non-existent then exit the programm with error.
	for item in config.items("twitch"):
		if item[0] == 'port':
			port = int(item[1])
		elif item[0] == 'channel':
			channel = item[1]
			request = requests.get("http://tmi.twitch.tv/servers?channel="+channel)
			if request.status_code == 200:
				# print type(request.json())
				host = random.choice(request.json()['servers']).split(':')[0]
				# print random.choice(request.json()['servers']).split(':')[0]
			
	
	# If any of the value are non-existent then exit the programm with error.
	if (host is None) or (port is None) or (channel is None):
		print "Config for twitch is not correct!"
		exit()
		
	# Creating new thread with queue in place for messaging tranfers
	tw = twThread(queue, host, port, channel)
	tw.start()