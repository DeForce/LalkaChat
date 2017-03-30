# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import re
from collections import OrderedDict
from modules.helper.module import MessagingModule
from modules.helper.system import IGNORED_TYPES

DEFAULT_PRIORITY = 30

CONF_DICT = OrderedDict()
CONF_DICT['gui_information'] = {
    'category': 'messaging',
    'id': DEFAULT_PRIORITY}
CONF_DICT['main'] = {'message': 'ignored message'}
CONF_DICT['users_hide'] = []
CONF_DICT['users_block'] = []
CONF_DICT['words_hide'] = []
CONF_DICT['words_block'] = []


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

    def process_message(self, message, queue, **kwargs):
        if message:
            if message['type'] in IGNORED_TYPES:
                return message

            if message['user'].lower() in self._conf_params['config']['users_hide']:
                return

            for word in self._conf_params['config']['words_hide']:
                if re.search(word, message['text'].encode('utf-8')):
                    return

            if message['user'].lower() in self._conf_params['config']['users_block']:
                message['text'] = self._conf_params['config']['main']['message']
                return message

            for word in self._conf_params['config']['words_block']:
                if re.search(word, message['text'].encode('utf-8')):
                    message['text'] = self._conf_params['config']['main']['message']
                    return message
            return message
