# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import ConfigParser
import threading
import importlib


class Message(threading.Thread):
    def __init__(self, queue):
        super(self.__class__, self).__init__()
        # Creating dict for dynamic modules
        self.modules = {}
        self.msg_counter = 0

        print "Loading configuration file for messaging"
        python_folder = os.path.dirname(os.path.abspath(__file__))
        conf_folder = os.path.join(python_folder, "conf")
        conf_file = os.path.join(conf_folder, "messaging.cfg")
        module_folder = os.path.join(python_folder, "modules", "messaging")
        module_tag = "modules.messaging"
        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(conf_file)
        # Dynamically loading the modules from cfg.
        if config.items("messaging") > 0:
            for module in config.items("messaging"):
                print "Loading %s" % module[0]
                # We load the module, and then we initalize it.
                # When writing your modules you should have class with the
                #  same name as module name
                tmp = importlib.import_module(module_tag + '.' + module[0])
                init = getattr(tmp, module[0])
                self.modules[module[0]] = init(conf_folder)
        self.daemon = "True"
        self.queue = queue
        self.start()

    def msg_process(self, message):
        if ('to' in message) and (message['to'] is not None):
            message['text'] = ', '.join([message['to'], message['text']])

        if 'id' not in message:
            message['id'] = self.msg_counter
            self.msg_counter += 1
        # When we receive message we pass it via all loaded modules
        # All modules should return the message with modified/not modified
        #  content so it can be passed to new module, or to pass to CLI

        for module in self.modules:
            try:
                message = self.modules[module].get_message(message)
            except:
                pass

        if message is not None:
            print "[%s] %s: %s" % (message['source'], message['user'], message['text'])

    def run(self):
        while True:
            message = self.queue.get()
            self.msg_process(message)
