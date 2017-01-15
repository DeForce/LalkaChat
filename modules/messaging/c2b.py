# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
# Copyright (C) 2016   CzT/Vladislav Ivanov
import logging
import os
import random
import re
from collections import OrderedDict
from modules.helper.parser import load_from_config_file
from modules.helper.module import MessagingModule
from modules.helper.system import IGNORED_TYPES

DEFAULT_PRIORITY = 10
log = logging.getLogger('c2b')


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


class c2b(MessagingModule):
    def __init__(self, conf_folder, **kwargs):
        MessagingModule.__init__(self)
        # Creating filter and replace strings.
        conf_file = os.path.join(conf_folder, "c2b.cfg")

        conf_dict = OrderedDict()
        conf_dict['gui_information'] = {
            'category': 'messaging',
            'id': DEFAULT_PRIORITY}
        conf_dict['config'] = {}

        conf_gui = {
            'config': {
                'addable': 'true',
                'view': 'list_dual'},
            'non_dynamic': ['config.*']}
        config = load_from_config_file(conf_file, conf_dict)
        self._conf_params.update(
            {'folder': conf_folder, 'file': conf_file,
             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
             'parser': config,
             'id': conf_dict['gui_information']['id'],
             'config': conf_dict,
             'gui': conf_gui})

    def process_message(self, message, queue, **kwargs):
        # Replacing the message if needed.
        # Please do the needful
        if message:
            if message['type'] in IGNORED_TYPES:
                return message

            for item, replace in self._conf_params['config']['config'].iteritems():
                item = item.decode('utf-8')
                if item in message['text']:
                    replace_word = random.choice(replace.split('/')).decode('utf-8')
                    if message['source'] == 'tw':
                        message['emotes'] = twitch_replace_indexes(item, message['text'],
                                                                   len(item), len(replace_word),
                                                                   message.get('emotes', []))
                    message['text'] = message['text'].replace(item, replace_word)
            return message
