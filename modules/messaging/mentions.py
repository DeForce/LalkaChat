# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
from modules.helper.message import process_text_messages, ignore_system_messages
from modules.helper.module import MessagingModule
from modules.interface.types import LCGridSingle, LCPanel

CONF_DICT = LCPanel()
CONF_DICT['mentions'] = LCGridSingle()
CONF_DICT['address'] = LCGridSingle()


class Mentions(MessagingModule):
    def __init__(self, *args, **kwargs):
        MessagingModule.__init__(self, config=CONF_DICT, *args, **kwargs)

    @process_text_messages
    @ignore_system_messages
    def _process_message(self, message, **kwargs):
        # Replacing the message if needed.
        # Please do the needful
        self._check_addressed(message)
        if not message.pm:
            self._check_mentions(message)
        return message

    def _check_mentions(self, message):
        for mention in self.get_config('mentions'):
            if mention in message.text.lower().split(' '):
                message.mention = True
                message.jsonable += ['mention']
                break

    def _check_addressed(self, message):
        for address in self.get_config('address'):
            if address == message.text.lower().split(' ')[0]:
                message.pm = True
                break
