# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import datetime
from collections import OrderedDict

from modules.helper.parser import self_heal
from modules.helper.modules import MessagingModule
from modules.helper.system import IGNORED_TYPES

DEFAULT_PRIORITY = 20


class logger(MessagingModule):
    def __init__(self, conf_folder, **kwargs):
        MessagingModule.__init__(self)
        # Creating filter and replace strings.
        conf_file = os.path.join(conf_folder, "logger.cfg")
        conf_dict = OrderedDict()
        conf_dict['gui_information'] = {
            'category': 'messaging',
            'id': DEFAULT_PRIORITY
        }
        conf_dict['config'] = OrderedDict()
        conf_dict['config']['logging'] = True
        conf_dict['config']['file_format'] = '%Y-%m-%d'
        conf_dict['config']['message_date_format'] = '%Y-%m-%d %H:%M:%S'
        conf_dict['config']['rotation'] = 'daily'
        conf_gui = {'non_dynamic': ['config.*']}

        config = self_heal(conf_file, conf_dict)
        self._conf_params = {'folder': conf_folder, 'file': conf_file,
                             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                             'parser': config,
                             'id': config.get('gui_information', 'id'),
                             'config': conf_dict,
                             'gui': conf_gui}

        tag_config = 'config'

        self.format = config.get(tag_config, 'file_format')
        self.ts_format = config.get(tag_config, 'message_date_format')
        self.logging = config.get(tag_config, 'logging')
        self.rotation = config.get(tag_config, 'logging')

        self.folder = 'logs'

        self.destination = os.path.join(conf_folder, '..', self.folder)
        if not os.path.exists(self.destination):
            os.makedirs(self.destination)

    def process_message(self, message, queue, **kwargs):
        if message:
            if message['type'] in IGNORED_TYPES:
                return message
            with open('{0}.txt'.format(
                    os.path.join(self.destination, datetime.datetime.now().strftime(self.format))), 'a') as f:
                f.write('[{3}] [{0}] {1}: {2}\n'.format(message['source'].encode('utf-8'),
                                                        message['user'].encode('utf-8'),
                                                        message['text'].encode('utf-8'),
                                                        datetime.datetime.now().strftime(self.ts_format).encode('utf-8')))
            return message
