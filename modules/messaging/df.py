# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import re
import os

from modules.helper.message import process_text_messages, ignore_system_messages
from modules.helper.module import MessagingModule
from modules.interface.types import LCStaticBox, LCText, LCGridDual, LCPanel

CONF_DICT = LCPanel()
CONF_DICT['grep'] = LCStaticBox()
CONF_DICT['grep']['symbol'] = LCText('#')
CONF_DICT['grep']['file'] = LCText('logs/df.txt')
CONF_DICT['prof'] = LCGridDual()

CONF_GUI = {'non_dynamic': ['grep.*']}


class DF(MessagingModule):
    def __init__(self, *args, **kwargs):
        MessagingModule.__init__(self, config=CONF_DICT, gui=CONF_GUI, *args, **kwargs)
        # Dwarf professions.
        self.file = str(CONF_DICT['grep']['file'])

        dir_name = os.path.dirname(self.file)
        if not os.path.exists(dir_name):
            os.makedirs(os.path.dirname(self.file))

        if not os.path.isfile(self.file):
            with open(self.file, 'w'):
                pass

    def write_to_file(self, user, role):
        with open(self.file, 'r') as f:
            for line in f.readlines():
                if user == line.split(',')[0]:
                    return
        with open(self.file, 'a') as a_file:
            a_file.write("{0},{1}\n".format(user, role))

    @process_text_messages
    @ignore_system_messages
    def _process_message(self, message, **kwargs):
        for role, regexp in self.get_config('prof').value.iteritems():
            if re.search('{0}{1}'.format(self.get_config('grep', 'symbol'), regexp).decode('utf-8'),
                         message.text):
                self.write_to_file(message.user, role.capitalize())
                break
        return message
