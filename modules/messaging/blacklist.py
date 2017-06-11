# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import re

import logging

from modules.helper.message import ignore_system_messages, process_text_messages
from modules.helper.module import MessagingModule
from modules.interface.types import LCStaticBox, LCText, LCGridSingle, LCPanel

DEFAULT_PRIORITY = 30

CONF_DICT = LCPanel()
CONF_DICT['gui_information'] = {
    'category': 'messaging',
    'id': DEFAULT_PRIORITY}
CONF_DICT['main'] = LCStaticBox()
CONF_DICT['main']['message'] = LCText('ignored message')
CONF_DICT['users_hide'] = LCGridSingle()
CONF_DICT['users_block'] = LCGridSingle()
CONF_DICT['words_hide'] = LCGridSingle()
CONF_DICT['words_block'] = LCGridSingle()
log = logging.getLogger('blacklist')


class blacklist(MessagingModule):
    def __init__(self, *args, **kwargs):
        MessagingModule.__init__(self, *args, **kwargs)

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self):
        return {
            'words_hide': {
                'addable': True,
                'view': 'list'},
            'words_block': {
                'addable': True,
                'view': 'list'},
            'users_hide': {
                'view': 'list',
                'addable': 'true'},
            'users_block': {
                'view': 'list',
                'addable': 'true'},
            'non_dynamic': ['main.*']
        }

    @process_text_messages
    @ignore_system_messages
    def process_message(self, message, **kwargs):
        self._blocked(message)
        if self._hidden(message):
            message.hidden = True
        return message

    def _hidden(self, message):
        if message.user.lower() in self._conf_params['config']['users_hide']:
            return True

        for word in self._conf_params['config']['words_hide']:
            if re.search(word, message.text.encode('utf-8')):
                return True

    def _blocked(self, message):
        if message.user.lower() in self._conf_params['config']['users_block']:
            message.text = self._conf_params['config']['main']['message']

        for word in self._conf_params['config']['words_block']:
            if re.search(word, message.text.encode('utf-8')):
                message.text = self._conf_params['config']['main']['message']
