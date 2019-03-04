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
        MessagingModule.__init__(self, config=CONF_DICT, gui=CONF_GUI, *args, **kwargs)
        self._load_priority = 20
        # Creating filter and replace strings.
        self.format = self.get_config('config', 'file_format')
        self.ts_format = str(self.get_config('config', 'message_date_format'))
        self.logging = self.get_config('config', 'logging')

        self.folder = 'logs'

        self.destination = os.path.join(CONF_FOLDER, '..', self.folder)
        if not os.path.exists(self.destination):
            os.makedirs(self.destination)

    @process_text_messages
    @ignore_system_messages
    def _process_message(self, message, **kwargs):
        log_file = os.path.join(self.destination, datetime.datetime.now().strftime(str(self.format)))
        with open(f'{log_file}.txt', 'a', encoding='utf-8') as f:
            time = datetime.datetime.now().strftime(self.ts_format)
            f.write(f'[{time}] [{message.platform.id}] [{message.channel_name}] {message.user}: '
                    f'{message.text}\n')
        return message
