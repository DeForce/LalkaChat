# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import ConfigParser
import threading
import imp
import codecs
import sys


class Message(threading.Thread):
    def __init__(self, queue):
        super(self.__class__, self).__init__()
        # Creating dict for dynamic modules
        self.modules = []
        self.modules_configs = []
        self.daemon = True
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
                join_path = [python_folder] + module_tag.split('.') + ['{0}.py'.format(module[0])]
                file_path = os.path.join(*join_path)

                tmp = imp.load_source(module[0], file_path)
                init = getattr(tmp, module[0])
                class_module = init(conf_folder)
                self.modules.append(class_module)
                self.modules_configs.append({module[0]: class_module.conf_params})
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
            message = module.get_message(message, self.queue)
            try:
                pass
            except Exception as exc:
                print exc

    def run(self):
        while True:
            UTF8Writer = codecs.getwriter('utf8')
            sys.stdout = UTF8Writer(sys.stdout)
            message = self.queue.get()
            self.msg_process(message)
