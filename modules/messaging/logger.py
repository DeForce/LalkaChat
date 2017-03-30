# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import os
import datetime
from collections import OrderedDict

from modules.helper.module import MessagingModule
from modules.helper.system import IGNORED_TYPES, CONF_FOLDER

DEFAULT_PRIORITY = 20

CONF_DICT = OrderedDict()
CONF_DICT['gui_information'] = {
    'category': 'messaging',
    'id': DEFAULT_PRIORITY
}
CONF_DICT['config'] = OrderedDict()
CONF_DICT['config']['logging'] = True
CONF_DICT['config']['file_format'] = '%Y-%m-%d'
CONF_DICT['config']['message_date_format'] = '%Y-%m-%d %H:%M:%S'
CONF_DICT['config']['rotation'] = 'daily'

CONF_GUI = {'non_dynamic': ['config.*']}


class logger(MessagingModule):
    def __init__(self, *args, **kwargs):
        MessagingModule.__init__(self, *args, **kwargs)
        # Creating filter and replace strings.
        self.format = CONF_DICT['config']['file_format']
        self.ts_format = CONF_DICT['config']['message_date_format']
        self.logging = CONF_DICT['config']['logging']
        self.rotation = CONF_DICT['config']['rotation']

        self.folder = 'logs'

        self.destination = os.path.join(CONF_FOLDER, '..', self.folder)
        if not os.path.exists(self.destination):
            os.makedirs(self.destination)

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self, *args, **kwargs):
        return CONF_GUI

    def process_message(self, message, queue, **kwargs):
        if message:
            if message['type'] in IGNORED_TYPES:
                return message
            with open('{0}.txt'.format(
                    os.path.join(self.destination, datetime.datetime.now().strftime(self.format))), 'a') as f:
                f.write('[{3}] [{0}] {1}: {2}\n'.format(
                    message['source'].encode('utf-8'),
                    message['user'].encode('utf-8'),
                    message['text'].encode('utf-8'),
                    datetime.datetime.now().strftime(self.ts_format).encode('utf-8')))
            return message
