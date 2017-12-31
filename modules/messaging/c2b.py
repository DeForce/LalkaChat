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


def twitch_replace_indexes(filter_name, text, filter_size, replace_size, emotes_list):
    emotes = []
    message_index_list = [m.start() for m in re.finditer(filter_name, text)]

    offset = replace_size - filter_size
    for emote_data in emotes_list:
        emote = {'emote_id': emote_data['emote_id'],
                 'emote_pos': []}
        for emote_pos in emote_data['emote_pos']:
            e_start, e_end = emote_pos.split('-')
            mod_offset = 0
            for index, item in enumerate(message_index_list):
                if item < int(e_start):
                    mod_offset = offset * (index + 1)
            emote['emote_pos'].append('{0}-{1}'.format(int(e_start) + mod_offset,
                                                       int(e_end) + mod_offset))
        emotes.append(emote)
    return emotes


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
            if item in message.text:
                replace_word = random.choice(replace.split('/'))
                message.text = re.sub(C2B_REGEXP.format(item),
                                      r'\1{}\3'.format(replace_word),
                                      message.text, flags=re.UNICODE)
        return message

    def _conf_settings(self, *args, **kwargs):
        return CONF_DICT

    def _gui_settings(self, *args, **kwargs):
        return CONF_GUI
