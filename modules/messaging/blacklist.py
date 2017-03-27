# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import re
import os
from collections import OrderedDict
from modules.helper.parser import load_from_config_file
from modules.helper.module import MessagingModule
from modules.helper.system import IGNORED_TYPES

DEFAULT_PRIORITY = 30


class blacklist(MessagingModule):
    def __init__(self, conf_folder, **kwargs):
        MessagingModule.__init__(self)
        # Dwarf professions.
        conf_file = os.path.join(conf_folder, "blacklist.cfg")

        # Ordered because order matters
        conf_dict = OrderedDict()
        conf_dict['gui_information'] = {
            'category': 'messaging',
            'id': DEFAULT_PRIORITY}
        conf_dict['main'] = {'message': 'ignored message'}
        conf_dict['users_hide'] = []
        conf_dict['users_block'] = []
        conf_dict['words_hide'] = []
        conf_dict['words_block'] = []

        conf_gui = {
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
            'non_dynamic': ['main.*']}
        config = load_from_config_file(conf_file, conf_dict)
        self._conf_params.update(
            {'folder': conf_folder, 'file': conf_file,
             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
             'parser': config,
             'id': conf_dict['gui_information']['id'],
             'config': OrderedDict(conf_dict),
             'gui': conf_gui})

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
