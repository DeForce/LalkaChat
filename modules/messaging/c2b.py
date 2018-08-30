# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import logging
import random
import re

from modules.helper.message import process_text_messages, ignore_system_messages
from modules.helper.module import MessagingModule
from modules.interface.types import LCGridDual, LCPanel

log = logging.getLogger('c2b')

CONF_DICT = LCPanel()
CONF_DICT['config'] = LCGridDual()

CONF_GUI = {
    'config': {
        'addable': 'true',
        'view': 'list_dual'},
    'non_dynamic': ['config.*']}
C2B_REGEXP = ur'(^|\s)({})(?=(\s|$))'


class C2B(MessagingModule):
    def __init__(self, *args, **kwargs):
        MessagingModule.__init__(self, *args, **kwargs)
        self._load_priority = 10

    @process_text_messages
    @ignore_system_messages
    def process_message(self, message, **kwargs):
        # Replacing the message if needed.
        # Please do the needful
        for item, replace in self._conf_params['config']['config'].iteritems():
            if item in message.text.split(' '):
                replace_word = random.choice(replace.split('/'))
                message.text = message.text.replace(item, replace_word)
        return message

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self, *args, **kwargs):
        return CONF_GUI
