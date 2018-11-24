# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import os
import datetime

from modules.helper.message import process_text_messages, ignore_system_messages
from modules.helper.module import MessagingModule
from modules.helper.system import CONF_FOLDER
from modules.interface.types import LCPanel, LCStaticBox, LCBool, LCText

CONF_DICT = LCPanel()
CONF_DICT['config'] = LCStaticBox()
CONF_DICT['config']['logging'] = LCBool(True)
CONF_DICT['config']['file_format'] = LCText('%Y-%m-%d')
CONF_DICT['config']['message_date_format'] = LCText('%Y-%m-%d %H:%M:%S')

CONF_GUI = {'non_dynamic': ['config.*']}


class Logger(MessagingModule):
    def __init__(self, *args, **kwargs):
        MessagingModule.__init__(self, *args, **kwargs)
        self._load_priority = 20
        # Creating filter and replace strings.
        self.format = CONF_DICT['config']['file_format']
        self.ts_format = str(CONF_DICT['config']['message_date_format'])
        self.logging = CONF_DICT['config']['logging']

        self.folder = 'logs'

        self.destination = os.path.join(CONF_FOLDER, '..', self.folder)
        if not os.path.exists(self.destination):
            os.makedirs(self.destination)

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self, *args, **kwargs):
        return CONF_GUI

    @process_text_messages
    @ignore_system_messages
    def process_message(self, message, **kwargs):
        with open('{0}.txt'.format(
                os.path.join(self.destination, datetime.datetime.now().strftime(str(self.format)))), 'a') as f:
            f.write('[{}] [{}] [{}] {}: {}\n'.format(
                datetime.datetime.now().strftime(self.ts_format).encode('utf-8'),
                message.platform.id.encode('utf-8'),
                message.channel_name,
                message.user.encode('utf-8'),
                message.text.encode('utf-8')))
        return message
