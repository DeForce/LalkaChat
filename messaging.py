# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import os
import threading
import operator
import logging
from collections import OrderedDict

from modules.helper.functions import get_class_from_iname
from modules.helper.module import BaseModule, MessagingModule
from modules.helper.system import ModuleLoadException, THREADS, CONF_FOLDER
from modules.helper.parser import load_from_config_file
from modules.interface.types import LCPanel, LCChooseMultiple

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
        self.queue = queue
        self.module_tag = "modules.messaging"
        self.threads = []

    def load_modules(self, main_config, settings):
        log.info("Loading configuration file for messaging")
        modules_list = OrderedDict()

        conf_file = os.path.join(main_config['conf_folder'], "messaging_modules.cfg")
        conf_dict = LCPanel()
        conf_dict['gui_information'] = {'category': 'messaging'}
        conf_dict['messaging'] = LCChooseMultiple(
            ['webchat'],
            check_type='files',
            folder='modules/messaging',
            keep_extension=False,
            description=True
        )

        conf_gui = {
            'non_dynamic': ['messaging.*']
        }
        config = load_from_config_file(conf_file, conf_dict)
        messaging_module = BaseModule(
            conf_params={
                'folder': main_config['conf_folder'], 'file': conf_file,
                'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                'parser': config,
                'config': conf_dict,
                'gui': conf_gui},
            conf_file_name='messaging_modules.cfg'
        )

        modules_list['messaging'] = messaging_module.conf_params()

        modules = {}
        # Loading modules from cfg.
        if len(conf_dict['messaging'].value) > 0:
            for m_module_name in conf_dict['messaging'].value:
                log.info("Loading %s" % m_module_name)
                # We load the module, and then we initalize it.
                # When writing your modules you should have class with the
                #  same name as module name
                join_path = [main_config['root_folder']] + self.module_tag.split('.') + ['{0}.py'.format(m_module_name)]
                file_path = os.path.join(*join_path)

                try:
                    class_init = get_class_from_iname(file_path, m_module_name)
                    class_module = class_init(main_config['conf_folder'],
                                              root_folder=main_config['root_folder'],
                                              main_settings=settings,
                                              conf_file=os.path.join(CONF_FOLDER, '{0}.cfg'.format(m_module_name)),
                                              queue=self.queue)

                    params = class_module.conf_params()
                    priority = params['config'].get('gui_information', {}).get('id', MODULE_PRI_DEFAULT)

                    if int(priority) in modules:
                        modules[int(priority)].append(class_module)
                    else:
                        modules[int(priority)] = [class_module]

                    modules_list[m_module_name.lower()] = params
                except ModuleLoadException:
                    log.error("Unable to load module {0}".format(m_module_name))
        sorted_module = sorted(modules.items(), key=operator.itemgetter(0))
        for sorted_priority, sorted_list in sorted_module:
            for sorted_list_item in sorted_list:
                self.modules.append(sorted_list_item)

        return modules_list

    def msg_process(self, message):
        # When we receive message we pass it via all loaded modules
        # All modules should return the message with modified/not modified
        #  content so it can be passed to new module, or to pass to CLI
        for m_module in self.modules:  # type: MessagingModule
            message = m_module.process_message(message, queue=self.queue)

    def run(self):
        for thread in range(THREADS):
            self.threads.append(MessageHandler(self.queue, self.msg_process))
            self.threads[thread].start()

