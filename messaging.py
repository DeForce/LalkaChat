# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import threading
import imp
import operator
import logging
from collections import OrderedDict

from main import CONF_FOLDER
from modules.helper.module import BaseModule
from modules.helper.system import ModuleLoadException, THREADS
from modules.helper.parser import load_from_config_file


log = logging.getLogger('messaging')
MODULE_PRI_DEFAULT = '100'


class MessageHandler(threading.Thread):
    def __init__(self, queue, process):
        self.queue = queue
        self.process = process
        threading.Thread.__init__(self)

    def run(self):
        while True:
            self.process(self.queue.get())


class Message(threading.Thread):
    def __init__(self, queue):
        super(self.__class__, self).__init__()
        # Creating dict for dynamic modules
        self.modules = []
        self.daemon = True
        self.msg_counter = 0
        self.queue = queue
        self.module_tag = "modules.messaging"
        self.threads = []

    def load_modules(self, main_config, settings):
        log.info("Loading configuration file for messaging")
        modules_list = OrderedDict()

        conf_file = os.path.join(main_config['conf_folder'], "messaging_modules.cfg")
        conf_dict = OrderedDict()
        conf_dict['gui_information'] = {'category': 'messaging'}
        conf_dict['messaging'] = {'webchat': None}

        conf_gui = {
            'messaging': {'check': 'modules/messaging',
                          'check_type': 'files',
                          'file_extension': False,
                          'view': 'choose_multiple',
                          'description': True},
            'non_dynamic': ['messaging.*']}
        config = load_from_config_file(conf_file, conf_dict)
        messaging_module = BaseModule(
            conf_params={
                'folder': main_config['conf_folder'], 'file': conf_file,
                'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                'parser': config,
                'config': conf_dict,
                'gui': conf_gui})

        modules_list['messaging'] = messaging_module.conf_params()

        modules = {}
        # Loading modules from cfg.
        if len(conf_dict['messaging']) > 0:
            for module, item in conf_dict['messaging'].iteritems():
                log.info("Loading %s" % module)
                # We load the module, and then we initalize it.
                # When writing your modules you should have class with the
                #  same name as module name
                join_path = [main_config['root_folder']] + self.module_tag.split('.') + ['{0}.py'.format(module)]
                file_path = os.path.join(*join_path)

                try:
                    tmp = imp.load_source(module, file_path)
                    class_init = getattr(tmp, module)
                    class_module = class_init(main_config['conf_folder'],
                                              root_folder=main_config['root_folder'],
                                              main_settings=settings,
                                              conf_file=os.path.join(CONF_FOLDER, '{0}.cfg'.format(module)))

                    params = class_module.conf_params()
                    if 'id' in params:
                        priority = params['id']
                    else:
                        priority = MODULE_PRI_DEFAULT

                    if int(priority) in modules:
                        modules[int(priority)].append(class_module)
                    else:
                        modules[int(priority)] = [class_module]

                    modules_list[module] = params
                except ModuleLoadException as exc:
                    log.error("Unable to load module {0}".format(module))
        sorted_module = sorted(modules.items(), key=operator.itemgetter(0))
        for sorted_priority, sorted_list in sorted_module:
            for sorted_list_item in sorted_list:
                self.modules.append(sorted_list_item)

        return modules_list

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
            message = module.process_message(message, self.queue)

    def run(self):
        for thread in range(THREADS):
            self.threads.append(MessageHandler(self.queue, self.msg_process))
            self.threads[thread].start()

