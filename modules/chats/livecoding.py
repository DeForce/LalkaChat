import os
import logging
import threading
import sleekxmpp
import Queue
import re
from modules.helpers.parser import FlagConfigParser

logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('livecoding')
SOURCE = "lc"
SOURCE_ICON = "https://www.livecoding.tv/static/img/favicon.ico"


class LivecodingMessageHandler(threading.Thread):
    def __init__(self, queue, lc_queue, **kwargs):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.message_queue = queue
        self.lc_queue = lc_queue
        self.source = SOURCE

        self.nickname = kwargs.get('nickname')

    def run(self):
        while True:
            self.process_message(self.lc_queue.get())

    def process_message(self, msg):
        comp = {'source': self.source,
                'source_icon': SOURCE_ICON,
                'user': msg['nickname'],
                'text': msg['body'],
                'emotes': []}

        if re.match('^{0},'.format(self.nickname).lower(), comp['text'].lower()):
            comp['pm'] = True
        self.message_queue.put(comp)


class lcChat(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password='', nickname='', queue=None, room=None, **kwargs):
        super(self.__class__, self).__init__(jid, password)

        if room is None:
            room = '{}@chat.livecoding.tv'.format(jid.user)
        # Received value setting.
        self.room = room
        self.nickname = nickname
        self._register_plugin_helper()
        self.lc_queue = Queue.Queue()

        message_handler = LivecodingMessageHandler(queue, self.lc_queue, nickname=nickname, **kwargs)
        message_handler.start()

        # Event Handlers
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("connected", self.connected)
        self.add_event_handler("groupchat_message", self.received_message)

    def _register_plugin_helper(self):
        self.register_plugin('xep_0030')
        self.register_plugin('xep_0004')
        self.register_plugin('xep_0060')
        self.register_plugin('xep_0199', {'keepalive': True, 'frequency': 60})
        self.register_plugin('xep_0045')

    def start(self, event):
        log.info("Session started")
        self.plugin['xep_0045'].joinMUC(self.room, self.nickname, wait=True)

    def connected(self, event):
        log.info("Connected to server")

    def disconnected(self, event):
        log.warning("Disconnected from server")

        # I'm not sure it works, but who knows?.. [Yumi]
        if self.connect():
            self.process(block=True)
        else:
            log.error("Unable to connect")

    def received_message(self, msg):
        message = {'nickname': msg['mucnick'], 'body': msg['body']}
        self.lc_queue.put(message)


class lcThread(threading.Thread):
    def __init__(self, queue, login, password, nickname):
        threading.Thread.__init__(self)
        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = "True"
        self.queue = queue
        self.login = login
        self.password = password
        self.nickname = nickname
        self.kwargs = {}

    def load_config(self):
        error = False
        # Smiles are hardcoded into livecoding chat module, so right now there's nothing instead of. [Yumi]

        # Livecoding asks you to be authenticated to even read chat, so we don't need to check if channel exists,
        # we just going to authenticate. [Yumi]

        # Function load_config() left to follow scheme of other modules. [Yumi]

        return error

    def run(self):
        if not self.load_config():
            # Connecting to livecoding xmpp server
            jid = sleekxmpp.JID(local=self.login, domain='livecoding.tv', resource='chat')
            xmpp = lcChat(jid, self.password, self.nickname, self.queue)
            if xmpp.connect():
                xmpp.process(block=True)
            else:
                log.error("Unable to connect")


class livecoding:
    def __init__(self, queue, python_folder, **kwargs):
        # Reading config from main directory.
        conf_folder = os.path.join(python_folder, "conf")

        log.info("Initializing livecoding chat")
        conf_file = os.path.join(conf_folder, "livecoding.cfg")
        config = FlagConfigParser(allow_no_value=True)
        if not os.path.exists(conf_file):
            config.add_section('gui_information')
            config.set('gui_information', 'category', 'chat')

            config.add_section('config')
            config.set('config', 'login', 'YOUR_LOGIN')
            config.set('config', 'password', 'YOUR_PASSWORD')
            config.set('config', 'nickname', 'YOUR_NICKNAME')

            config.write(open(conf_file, 'w'))

        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config}

        config.read(conf_file)
        # Checking config file for needed variables
        conf_tag = 'config'
        lc_login = config.get_or_default(conf_tag, 'login', 'YOUR_LOGIN')
        lc_password = config.get_or_default(conf_tag, 'password', 'YOUR_PASSWORD')
        lc_nickname = config.get_or_default(conf_tag, 'nickname', 'YOUR_NICKNAME')

        # Creating new thread with queue in place for messaging transfers
        lc = lcThread(queue, lc_login, lc_password, lc_nickname)
        lc.start()
