# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import logging
import random

from modules.helper.message import process_text_messages, ignore_system_messages
from modules.helper.module import MessagingModule
from modules.interface.types import LCGridDual, LCPanel

log = logging.getLogger('c2b')

CONF_DICT = LCPanel()
CONF_DICT['config'] = LCGridDual()

C2B_REGEXP = ur'(^|\s)({})(?=(\s|$))'


class C2B(MessagingModule):
    def __init__(self, *args, **kwargs):
        MessagingModule.__init__(self, config=CONF_DICT, *args, **kwargs)
        self._load_priority = 10

    @process_text_messages
    @ignore_system_messages
    def _process_message(self, message, **kwargs):
        # Replacing the message if needed.
        # Please do the needful
        for item, replace in self.get_config('config').value.iteritems():
            if item in message.text.split(' '):
                replace_word = random.choice(replace.split('/'))
                message.text = message.text.replace(item, replace_word)
        return message
