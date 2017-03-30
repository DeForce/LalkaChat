# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import re
from collections import OrderedDict

from modules.helper.module import MessagingModule
from modules.helper.system import IGNORED_TYPES

CONF_DICT = OrderedDict()
CONF_DICT['gui_information'] = {'category': 'messaging'}
CONF_DICT['mentions'] = []
CONF_DICT['address'] = []

CONF_GUI = {
    'mentions': {
        'addable': 'true',
        'view': 'list'},
    'address': {
        'addable': 'true',
        'view': 'list'}
}


class mentions(MessagingModule):
    def __init__(self, *args, **kwargs):
        MessagingModule.__init__(self, *args, **kwargs)
        # Creating filter and replace strings.

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self, *args, **kwargs):
        return CONF_GUI

    def process_message(self, message, queue, **kwargs):
        # Replacing the message if needed.
        # Please do the needful
        if message:
            if message['type'] in IGNORED_TYPES:
                return message

            for mention in self._conf_params['config']['mentions']:
                if re.search(mention, message['text'].lower()):
                    message['mention'] = True
                    break

            for address in self._conf_params['config']['address']:
                if re.match(address, message['text'].lower()):
                    message['pm'] = True
                    break

            if 'mention' in message and 'pm' in message:
                message.pop('mention')

            return message
