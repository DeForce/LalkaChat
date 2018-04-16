# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2018   CzT/Vladislav Ivanov
import logging

from modules.helper.message import process_text_messages, ignore_system_messages, SystemMessage
from modules.helper.module import MessagingModule
from modules.interface.types import LCPanel, LCBool, LCStaticBox, LCText

log = logging.getLogger('c2b')

CONF_DICT = LCPanel()
CONF_DICT['config'] = LCStaticBox()
CONF_DICT['config']['enabled'] = LCBool(True)
CONF_DICT['config']['only_gui'] = LCBool(True)
CONF_DICT['config']['welcome_msg'] = LCText("{}, welcome to the stream!")

CONF_GUI = {
    'config': {}
}
C2B_REGEXP = ur'(^|\s)({})(?=(\s|$))'


class Welcome(MessagingModule):
    def __init__(self, *args, **kwargs):
        MessagingModule.__init__(self, *args, **kwargs)
        self.clients = []

    def welcome_message(self, user):
        self._msg_queue.put(SystemMessage(
            self._conf_params['config']['config']['welcome_msg'].format(user),
            category='module',
            only_gui=self._conf_params['config']['config']['only_gui']
        ))

    @process_text_messages
    @ignore_system_messages
    def process_message(self, message, **kwargs):
        # Replacing the message if needed.
        # Please do the needful
        if message.user not in self.clients:
            self.clients.append(message.user)
            self.welcome_message(message.user)

        return message

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self, *args, **kwargs):
        return CONF_GUI
