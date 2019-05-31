# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import re

import logging

from modules.helper.message import ignore_system_messages, process_text_messages
from modules.helper.module import MessagingModule
from modules.interface.types import LCStaticBox, LCText, LCGridSingle, LCPanel


CONF_DICT = LCPanel()
CONF_DICT['main'] = LCStaticBox()
CONF_DICT['main']['message'] = LCText('ignored message')
CONF_DICT['users_hide'] = LCGridSingle()
CONF_DICT['users_block'] = LCGridSingle()
CONF_DICT['words_hide'] = LCGridSingle()
CONF_DICT['words_block'] = LCGridSingle()
log = logging.getLogger('blacklist')

GUI = {
    'non_dynamic': ['main.*']
}


class Blacklist(MessagingModule):
    def __init__(self, *args, **kwargs):
        super(Blacklist, self).__init__(config=CONF_DICT, gui=GUI, *args, **kwargs)

    @property
    def users_hide(self):
        return self.get_config('users_hide')

    @property
    def words_hide(self):
        return self.get_config('words_hide')

    @property
    def users_block(self):
        return self.get_config('users_block')

    @property
    def words_block(self):
        return self.get_config('words_block')

    @property
    def message(self):
        return self.get_config('main', 'message').simple()

    @process_text_messages
    @ignore_system_messages
    def _process_message(self, message, **kwargs):
        self._blocked(message)
        if self._bl_hidden(message):
            message.hidden = True
        return message

    def _bl_hidden(self, message):
        if message.user.lower() in self.users_hide:
            return True

        for word in self.words_hide:
            if re.search(word, message.text):
                return True

    def _blocked(self, message):
        if message.user.lower() in self.users_block:
            message.text = self.message

        for word in self.words_block:
            if re.search(word, message.text):
                message.text = self.message
