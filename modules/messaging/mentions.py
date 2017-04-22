# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import re
from collections import OrderedDict

from modules.helper.message import process_text_messages, ignore_system_messages
from modules.helper.module import MessagingModule
from modules.interface.types import LCGridSingle, LCPanel

CONF_DICT = LCPanel()
CONF_DICT['gui_information'] = {'category': 'messaging'}
CONF_DICT['mentions'] = LCGridSingle()
CONF_DICT['address'] = LCGridSingle()

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

    @process_text_messages
    @ignore_system_messages
    def process_message(self, message, **kwargs):
        # Replacing the message if needed.
        # Please do the needful
        self._check_addressed(message)
        if not message.pm:
            self._check_mentions(message)
        return message

    def _check_mentions(self, message):
        for mention in self._conf_params['config']['mentions']:
            if re.search(mention, message.text.lower()):
                message.mention = True
                message.jsonable += ['mention']
                break

    def _check_addressed(self, message):
        for address in self._conf_params['config']['address']:
            if re.match(address, message.text.lower()):
                message.pm = True
                break
