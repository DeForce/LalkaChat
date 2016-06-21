import os
import ConfigParser
import threading
import importlib


class Message(threading.Thread):
    def __init__(self, queue):
        super(self.__class__, self).__init__()
        # Creating dict for dynamic modules
        self.modules={}

        print "Loading configuration file for messaging"
        pythonFolder=os.path.dirname(os.path.abspath(__file__))
        confFolder=os.path.join(pythonFolder, "conf")
        confFile=os.path.join(confFolder, "messaging.cfg")
        moduleFolder=os.path.join(pythonFolder, "modules", "messaging")
        moduleTag="modules.messaging"
        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(confFile)
        # Dynamically loading the modules from cfg.
        if config.items("messaging") > 0:
            for module in config.items("messaging"):
                print "Loading %s" % module[0]
                # We load the module, and then we initalize it.
                # When writing your modules you should have class with the
                #  same name as module name
                tmp = importlib.import_module(moduleTag + '.' + module[0])
                init =  getattr(tmp, module[0])
                self.modules[module[0]] = init(confFolder)
        self.daemon = "True"
        self.queue = queue
        self.start()

    def msgProcess(self, message):
        # When we receive message we pass it via all loaded modules
        # All modules should return the message with modified/not modified
        #  content so it can be passed to new module, or to pass to CLI
        for module in self.modules:
            message = self.modules[module].getMessage(message)

        source = message['source']
        username = message['user']
        text = message['text']

        if 'flags' in message:
            if message['flags'] == 'hidden':
                return

        print "[%s] %s: %s" %(source, username, text)

    def run(self):
        while True:
            message = self.queue.get()
            self.msgProcess(message)